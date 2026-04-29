from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Chapter, Lesson, Standard


class LessonDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create_chapter(self, subject: str, domain: str) -> Chapter:
        """Return existing chapter for this subject+domain, or create it."""
        result = await self.session.execute(
            select(Chapter).where(Chapter.subject == subject, Chapter.title == domain)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return existing

        count_result = await self.session.execute(
            select(func.count()).select_from(Chapter).where(Chapter.subject == subject)
        )
        next_order = (count_result.scalar_one() or 0) + 1

        chapter = Chapter(subject=subject, title=domain, order_index=next_order)
        self.session.add(chapter)
        await self.session.flush()
        await self.session.refresh(chapter)
        return chapter

    async def get_chapters_by_subject(self, subject: str) -> list[Chapter]:
        result = await self.session.execute(
            select(Chapter).where(Chapter.subject == subject).order_by(Chapter.order_index)
        )
        return list(result.scalars().all())

    async def get_lessons_by_chapter(self, chapter_id: UUID) -> list[Lesson]:
        result = await self.session.execute(
            select(Lesson).where(Lesson.chapter_id == chapter_id).order_by(Lesson.order_index)
        )
        return list(result.scalars().all())

    async def get_lesson_by_id(self, lesson_id: UUID) -> Optional[Lesson]:
        result = await self.session.execute(select(Lesson).where(Lesson.id == lesson_id))
        return result.scalar_one_or_none()

    async def get_lesson_by_standard(self, standard_id: UUID) -> Optional[Lesson]:
        result = await self.session.execute(select(Lesson).where(Lesson.standard_id == standard_id))
        return result.scalar_one_or_none()

    async def create_lesson(
        self,
        chapter_id: UUID,
        standard_id: Optional[UUID],
        subject: str,
        title: str,
        difficulty: str,
        order_index: int,
        content: dict,
    ) -> Lesson:
        lesson = Lesson(
            chapter_id=chapter_id,
            standard_id=standard_id,
            subject=subject,
            title=title,
            difficulty=difficulty,
            order_index=order_index,
            content=content,
        )
        self.session.add(lesson)
        await self.session.flush()
        await self.session.refresh(lesson)
        return lesson

    async def count_lessons_in_chapter(self, chapter_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Lesson).where(Lesson.chapter_id == chapter_id)
        )
        return result.scalar_one()

    async def get_standard_by_code(self, code: str) -> Optional[Standard]:
        result = await self.session.execute(select(Standard).where(Standard.code == code))
        return result.scalar_one_or_none()

    async def create_standard(
        self,
        code: str,
        subject: str,
        grade_level: int,
        title: str,
        description: Optional[str],
    ) -> Standard:
        standard = Standard(
            code=code,
            subject=subject,
            grade_level=grade_level,
            title=title,
            description=description,
        )
        self.session.add(standard)
        await self.session.flush()
        await self.session.refresh(standard)
        return standard

    async def count_standards(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(Standard))
        return result.scalar_one()
