import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.clients.claude_client import ClaudeClient
from app.daos.learner_dao import LearnerDAO
from app.daos.lesson_dao import LessonDAO
from app.daos.progress_dao import ProgressDAO
from app.services.grading import (
    compute_effective_stars,
    compute_level,
    compute_new_streak,
    compute_quiz_xp,
    compute_stars,
    grade_exercise,
)
from app.services.lesson_service import sanitize_lesson_content

QUIZ_SYSTEM_PROMPT = """You are an educational content creator for Smarty Steps,
a learning app for children ages 5-8.

Generate a personalized chapter quiz as valid JSON with this schema:
{
  "exercises": [
    // 7-10 exercises, mix of multiple_choice, fill_blank, matching types
    // Same format as lesson exercises, including correct answers
  ]
}

Set exercise difficulty based on the provided learner performance data.
Return ONLY the JSON object, no markdown fences."""


class QuizService:
    def __init__(
        self,
        lesson_dao: LessonDAO,
        progress_dao: ProgressDAO,
        claude: ClaudeClient,
        learner_dao: LearnerDAO,
    ):
        self.lesson_dao = lesson_dao
        self.progress_dao = progress_dao
        self.claude = claude
        self.learner_dao = learner_dao

    async def generate_quiz(self, learner_id: UUID, chapter_id: UUID) -> None:
        existing = await self.progress_dao.get_chapter_quiz(learner_id, chapter_id)
        if existing:
            return

        lessons = await self.lesson_dao.get_lessons_by_chapter(chapter_id)
        all_progress = await self.progress_dao.get_all_progress_for_learner(learner_id)
        prog_map = {p.lesson_id: p for p in all_progress}

        star_values = [
            prog_map[lesson.id].stars_earned if lesson.id in prog_map else 0 for lesson in lessons
        ]
        avg_stars = sum(star_values) / len(star_values) if star_values else 0
        difficulty = "hard" if avg_stars >= 2.5 else "medium" if avg_stars >= 1.5 else "easy"

        lesson_summaries = "\n".join(
            f"- {lesson.title} (stars: {prog_map[lesson.id].stars_earned if lesson.id in prog_map else 0}/3)"  # noqa: E501
            for lesson in lessons
        )
        user_message = (
            f"Generate a chapter quiz (difficulty: {difficulty}).\n"
            f"Learner performance:\n{lesson_summaries}\n"
            f"Focus on weaker areas. Return only the JSON."
        )

        import anthropic

        from app.core.config import settings

        client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model="claude-opus-4-7",
            max_tokens=3000,
            system=[
                {
                    "type": "text",
                    "text": QUIZ_SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_message}],
        )
        content = json.loads(response.content[0].text.strip())
        await self.progress_dao.create_chapter_quiz(
            learner_id=learner_id,
            chapter_id=chapter_id,
            difficulty=difficulty,
            content=content,
        )

    async def get_quiz(self, quiz_id: UUID) -> dict:
        quiz = await self.progress_dao.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise HTTPException(status_code=404, detail="Quiz not found or not yet generated")
        sanitized = sanitize_lesson_content({"exercises": quiz.content.get("exercises", [])})
        return {"id": quiz.id, "difficulty": quiz.difficulty, "exercises": sanitized["exercises"]}

    async def check_quiz_answer(self, quiz_id: UUID, exercise_id: str, answer: dict) -> dict:
        quiz = await self.progress_dao.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise HTTPException(status_code=404, detail="Quiz not found")
        exercises = quiz.content.get("exercises", [])
        exercise = next((e for e in exercises if e["id"] == exercise_id), None)
        if exercise is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        correct = grade_exercise(exercise, answer)
        explanation = exercise.get("explanation") if correct else None
        return {"correct": correct, "explanation": explanation}

    async def submit_quiz(
        self,
        parent,
        quiz_id: UUID,
        time_seconds: int,
        answers: dict[str, dict[str, Any]],
        learner_svc,
    ) -> dict:
        quiz = await self.progress_dao.get_quiz_by_id(quiz_id)
        if quiz is None:
            raise HTTPException(status_code=404, detail="Quiz not found")

        # learner_svc.get verifies the learner exists and belongs to the parent
        learner = await learner_svc.get(parent, quiz.learner_id)
        exercises = quiz.content.get("exercises", [])
        missing = [e["id"] for e in exercises if e["id"] not in answers]
        if missing:
            raise HTTPException(status_code=422, detail=f"Missing answers for: {missing}")

        correct_count = sum(grade_exercise(e, answers[e["id"]]) for e in exercises)
        total = len(exercises)
        new_stars = compute_stars(correct_count, total)
        new_effective = compute_effective_stars(new_stars)
        new_xp = compute_quiz_xp(new_stars)

        old_effective = compute_effective_stars(quiz.stars_earned or 0)
        effective_delta = new_effective - old_effective

        await self.progress_dao.update_quiz(
            quiz, stars=new_stars, correct=correct_count, total=total, time_seconds=time_seconds
        )

        old_level = compute_level(learner.xp or 0)
        if effective_delta > 0:
            xp_delta = new_xp - compute_quiz_xp(quiz.stars_earned or 0)
            new_streak = compute_new_streak(learner.streak_days or 0, learner.last_active_at)
            await self.learner_dao.update_stats(
                learner,
                star_delta=effective_delta,
                xp_delta=xp_delta,
                new_streak=new_streak,
                new_last_active_at=datetime.now(timezone.utc),
            )
            new_level = compute_level((learner.xp or 0) + xp_delta)
        else:
            new_level = old_level

        return {
            "stars_earned": new_stars,
            "effective_stars": new_effective,
            "correct": correct_count,
            "total": total,
            "xp_earned": new_xp,
            "level_up": new_level > old_level,
            "new_level": new_level,
        }
