from app.clients.claude_client import ClaudeClient
from app.clients.standards_api import StandardsAPIClient
from app.daos.lesson_dao import LessonDAO

SUBJECTS = ["math", "science", "english"]
GRADE_LEVELS = [0, 1, 2, 3]

_DIFFICULTY_BY_ORDER_INDEX = {1: "easy", 2: "easy", 3: "medium", 4: "medium", 5: "hard"}


class ContentService:
    def __init__(
        self, lesson_dao: LessonDAO, standards_api: StandardsAPIClient, claude: ClaudeClient
    ):
        self.dao = lesson_dao
        self.standards_api = standards_api
        self.claude = claude

    async def sync_subject_grade(self, subject: str, grade_level: int) -> None:
        """Fetch standards, auto-create chapters from domains, generate lessons. Idempotent."""
        standards = await self.standards_api.fetch_standards(subject, grade_level)

        for standard_data in standards:
            existing_standard = await self.dao.get_standard_by_code(standard_data.code)
            if existing_standard:
                existing_lesson = await self.dao.get_lesson_by_standard(existing_standard.id)
                if existing_lesson:
                    continue
                standard = existing_standard
            else:
                standard = await self.dao.create_standard(
                    code=standard_data.code,
                    subject=standard_data.subject,
                    grade_level=standard_data.grade_level,
                    title=standard_data.title,
                    description=standard_data.description,
                )

            chapter = await self.dao.get_or_create_chapter(
                subject=subject,
                domain=standard_data.domain,
            )

            order_index = (await self.dao.count_lessons_in_chapter(chapter.id)) + 1
            difficulty = _DIFFICULTY_BY_ORDER_INDEX.get(order_index, "hard")

            content = await self.claude.generate_lesson(
                standard_title=standard_data.title,
                standard_description=standard_data.description or standard_data.title,
                subject=subject,
                grade_level=grade_level,
            )
            await self.dao.create_lesson(
                chapter_id=chapter.id,
                standard_id=standard.id,
                subject=subject,
                title=standard_data.title,
                difficulty=difficulty,
                order_index=order_index,
                content=content,
            )

    async def sync_all(self) -> None:
        """Full sync across all subjects and grade levels. Idempotent."""
        for subject in SUBJECTS:
            for grade_level in GRADE_LEVELS:
                await self.sync_subject_grade(subject, grade_level)
