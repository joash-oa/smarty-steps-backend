import asyncio
import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException

from app.daos.learner_dao import LearnerDAO
from app.daos.lesson_dao import LessonDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Parent
from app.services.grading import (
    compute_level,
    compute_new_streak,
    compute_stars,
    compute_xp,
    grade_exercise,
)

logger = logging.getLogger(__name__)


class ProgressService:
    def __init__(self, lesson_dao: LessonDAO, progress_dao: ProgressDAO, learner_dao: LearnerDAO):
        self.lesson_dao = lesson_dao
        self.progress_dao = progress_dao
        self.learner_dao = learner_dao

    async def check_lesson_answer(self, lesson_id: UUID, exercise_id: str, answer: dict) -> dict:
        lesson = await self.lesson_dao.get_lesson_by_id(lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="Lesson not found")
        exercises = lesson.content.get("exercises", [])
        exercise = next((e for e in exercises if e["id"] == exercise_id), None)
        if exercise is None:
            raise HTTPException(status_code=404, detail="Exercise not found")
        correct = grade_exercise(exercise, answer)
        explanation = exercise.get("explanation") if correct else None
        return {"correct": correct, "explanation": explanation}

    async def submit_lesson(
        self,
        parent: Parent,
        learner_id: UUID,
        lesson_id: UUID,
        time_seconds: int,
        answers: dict[str, dict[str, Any]],
        learner_svc,
    ) -> dict:
        lesson = await self.lesson_dao.get_lesson_by_id(lesson_id)
        if lesson is None:
            raise HTTPException(status_code=404, detail="Lesson not found")

        learner = await learner_svc.get(parent, learner_id)
        exercises = lesson.content.get("exercises", [])

        missing = [e["id"] for e in exercises if e["id"] not in answers]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Missing answers for exercises: {missing}",
            )

        correct_count = sum(grade_exercise(e, answers[e["id"]]) for e in exercises)
        total = len(exercises)
        new_stars = compute_stars(correct_count, total)
        new_xp = compute_xp(new_stars)

        existing = await self.progress_dao.get_lesson_progress(learner.id, lesson_id)
        old_stars = existing.stars_earned if existing else 0
        star_delta = new_stars - old_stars

        if existing is None:
            await self.progress_dao.create_lesson_progress(
                learner_id=learner.id,
                lesson_id=lesson_id,
                stars=new_stars,
                correct=correct_count,
                total=total,
                time_seconds=time_seconds,
            )
        elif star_delta > 0:
            await self.progress_dao.update_lesson_progress(
                existing,
                stars=new_stars,
                correct=correct_count,
                total=total,
                time_seconds=time_seconds,
            )

        old_level = compute_level(learner.xp or 0)
        if star_delta > 0:
            xp_delta = new_xp - compute_xp(old_stars)
            new_streak = compute_new_streak(learner.streak_days or 0, learner.last_active_at)
            await self.learner_dao.update_stats(
                learner,
                star_delta=star_delta,
                xp_delta=xp_delta,
                new_streak=new_streak,
                new_last_active_at=datetime.now(timezone.utc),
            )
            new_level = compute_level((learner.xp or 0) + xp_delta)
        else:
            new_level = old_level

        # Only check for chapter completion on first lesson completion (not replays)
        if existing is None:
            total_in_chapter = await self.lesson_dao.count_lessons_in_chapter(lesson.chapter_id)
            completed_in_chapter = await self.progress_dao.count_completed_lessons_in_chapter(
                learner.id, lesson.chapter_id
            )
            if total_in_chapter > 0 and completed_in_chapter >= total_in_chapter:
                existing_quiz = await self.progress_dao.get_chapter_quiz(
                    learner.id, lesson.chapter_id
                )
                if existing_quiz is None:
                    asyncio.create_task(self._generate_quiz(learner.id, lesson.chapter_id))

        return {
            "stars_earned": new_stars,
            "correct": correct_count,
            "total": total,
            "xp_earned": new_xp,
            "level_up": new_level > old_level,
            "new_level": new_level,
        }

    async def _generate_quiz(self, learner_id: UUID, chapter_id: UUID) -> None:
        from app.clients.claude_client import get_claude_client
        from app.daos.lesson_dao import LessonDAO
        from app.daos.progress_dao import ProgressDAO
        from app.db.session import AsyncSessionLocal
        from app.services.quiz_service import QuizService

        try:
            async with AsyncSessionLocal() as session:
                svc = QuizService(
                    lesson_dao=LessonDAO(session),
                    progress_dao=ProgressDAO(session),
                    claude=get_claude_client(),
                )
                await svc.generate_quiz(learner_id, chapter_id)
                await session.commit()
        except Exception:
            logger.exception(
                "Background quiz generation failed for learner=%s chapter=%s",
                learner_id,
                chapter_id,
            )

    async def get_summary(self, parent, learner_id: UUID, learner_svc) -> dict:
        learner = await learner_svc.get(parent, learner_id)
        subjects = ["math", "science", "english"]
        summary = []
        for subject in subjects:
            all_progress = await self.progress_dao.get_progress_for_learner_subject(
                learner.id, subject
            )
            completed = [p for p in all_progress if p.completed]
            total_stars = sum(p.stars_earned for p in completed)
            summary.append(
                {
                    "subject": subject,
                    "lessons_completed": len(completed),
                    "lessons_total": len(all_progress),
                    "total_stars": total_stars,
                    "chapters_completed": 0,
                }
            )
        return {"summary": summary}

    async def get_subject_progress(
        self, parent, learner_id: UUID, subject: str, learner_svc
    ) -> dict:
        from app.services.lesson_service import compute_effective_stars

        learner = await learner_svc.get(parent, learner_id)
        chapters = await self.lesson_dao.get_chapters_by_subject(subject)
        chapter_details = []
        for chapter in chapters:
            lessons = await self.lesson_dao.get_lessons_by_chapter(chapter.id)
            all_prog = await self.progress_dao.get_all_progress_for_learner(learner.id)
            prog_map = {p.lesson_id: p for p in all_prog}
            quiz = await self.progress_dao.get_chapter_quiz(learner.id, chapter.id)
            lesson_details = []
            for lesson in sorted(lessons, key=lambda x: x.order_index):
                prog = prog_map.get(lesson.id)
                lesson_details.append(
                    {
                        "id": lesson.id,
                        "title": lesson.title,
                        "difficulty": lesson.difficulty,
                        "completed": prog.completed if prog else False,
                        "stars_earned": prog.stars_earned if prog else 0,
                        "score_correct": prog.score_correct if prog else None,
                        "score_total": prog.score_total if prog else None,
                    }
                )
            chapter_details.append(
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "order_index": chapter.order_index,
                    "quiz_completed": quiz.completed if quiz else False,
                    "quiz_stars_earned": quiz.stars_earned if quiz else 0,
                    "quiz_effective_stars": compute_effective_stars(
                        quiz.stars_earned if quiz else 0
                    ),
                    "lessons": lesson_details,
                }
            )
        return {"subject": subject, "chapters": chapter_details}
