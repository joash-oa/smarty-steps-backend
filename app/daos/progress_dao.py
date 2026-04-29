from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ChapterQuiz, Lesson, LessonProgress


class ProgressDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_lesson_progress(
        self, learner_id: UUID, lesson_id: UUID
    ) -> Optional[LessonProgress]:
        result = await self.session.execute(
            select(LessonProgress).where(
                LessonProgress.learner_id == learner_id,
                LessonProgress.lesson_id == lesson_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_lesson_progress(
        self,
        learner_id: UUID,
        lesson_id: UUID,
        stars: int,
        correct: int,
        total: int,
        time_seconds: int,
    ) -> LessonProgress:
        progress = LessonProgress(
            learner_id=learner_id,
            lesson_id=lesson_id,
            completed=True,
            stars_earned=stars,
            score_correct=correct,
            score_total=total,
            time_seconds=time_seconds,
            completed_at=datetime.now(timezone.utc),
        )
        self.session.add(progress)
        await self.session.flush()
        await self.session.refresh(progress)
        return progress

    async def update_lesson_progress(
        self,
        progress: LessonProgress,
        stars: int,
        correct: int,
        total: int,
        time_seconds: int,
    ) -> LessonProgress:
        progress.stars_earned = stars
        progress.score_correct = correct
        progress.score_total = total
        progress.time_seconds = time_seconds
        await self.session.flush()
        await self.session.refresh(progress)
        return progress

    async def get_all_progress_for_learner(self, learner_id: UUID) -> list[LessonProgress]:
        result = await self.session.execute(
            select(LessonProgress).where(LessonProgress.learner_id == learner_id)
        )
        return list(result.scalars().all())

    async def get_progress_for_learner_subject(
        self, learner_id: UUID, subject: str
    ) -> list[LessonProgress]:
        result = await self.session.execute(
            select(LessonProgress)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .where(LessonProgress.learner_id == learner_id, Lesson.subject == subject)
        )
        return list(result.scalars().all())

    async def count_completed_lessons_in_chapter(self, learner_id: UUID, chapter_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(LessonProgress)
            .join(Lesson, LessonProgress.lesson_id == Lesson.id)
            .where(
                LessonProgress.learner_id == learner_id,
                Lesson.chapter_id == chapter_id,
                LessonProgress.completed == True,  # noqa: E712
            )
        )
        return result.scalar_one()

    async def get_chapter_quiz(self, learner_id: UUID, chapter_id: UUID) -> Optional[ChapterQuiz]:
        result = await self.session.execute(
            select(ChapterQuiz).where(
                ChapterQuiz.learner_id == learner_id,
                ChapterQuiz.chapter_id == chapter_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_quiz_by_id(self, quiz_id: UUID) -> Optional[ChapterQuiz]:
        result = await self.session.execute(select(ChapterQuiz).where(ChapterQuiz.id == quiz_id))
        return result.scalar_one_or_none()

    async def create_chapter_quiz(
        self,
        learner_id: UUID,
        chapter_id: UUID,
        difficulty: str,
        content: dict,
    ) -> ChapterQuiz:
        quiz = ChapterQuiz(
            learner_id=learner_id,
            chapter_id=chapter_id,
            difficulty=difficulty,
            content=content,
        )
        self.session.add(quiz)
        await self.session.flush()
        await self.session.refresh(quiz)
        return quiz

    async def update_quiz(
        self,
        quiz: ChapterQuiz,
        stars: int,
        correct: int,
        total: int,
        time_seconds: int,
    ) -> ChapterQuiz:
        quiz.stars_earned = stars
        quiz.score_correct = correct
        quiz.score_total = total
        quiz.time_seconds = time_seconds
        quiz.completed = True
        quiz.completed_at = datetime.now(timezone.utc)
        await self.session.flush()
        await self.session.refresh(quiz)
        return quiz
