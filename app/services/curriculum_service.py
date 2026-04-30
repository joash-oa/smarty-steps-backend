from uuid import UUID

from app.core.exceptions import LessonNotFoundError
from app.daos.lesson_dao import LessonDAO
from app.daos.progress_dao import ProgressDAO
from app.services.grading import compute_effective_stars
from app.services.lesson_service import compute_lock_states, sanitize_lesson_content


class CurriculumService:
    def __init__(self, lesson_dao: LessonDAO, progress_dao: ProgressDAO):
        self.lesson_dao = lesson_dao
        self.progress_dao = progress_dao

    async def get_curriculum(self, parent, learner_id: UUID, subject: str, learner_svc) -> dict:
        learner = await learner_svc.get(parent, learner_id)

        chapters = await self.lesson_dao.get_chapters_by_subject(subject)
        all_progress = await self.progress_dao.get_all_progress_for_learner(learner.id)
        completed_lesson_ids = {p.lesson_id for p in all_progress if p.completed}
        progress_by_lesson_id = {p.lesson_id: p for p in all_progress}

        lessons_by_chapter = {
            chapter.id: await self.lesson_dao.get_lessons_by_chapter(chapter.id)
            for chapter in chapters
        }
        lock_states = compute_lock_states(
            chapters=chapters,
            lessons_by_chapter=lessons_by_chapter,
            completed_lesson_ids=completed_lesson_ids,
        )

        chapter_responses = []
        for chapter in chapters:
            lessons = lessons_by_chapter.get(chapter.id, [])
            quiz_record = await self.progress_dao.get_chapter_quiz(learner.id, chapter.id)
            all_lessons_complete = (
                all(lesson.id in completed_lesson_ids for lesson in lessons) if lessons else False
            )

            if not lessons or not all_lessons_complete:
                quiz_state = {
                    "id": None,
                    "locked": True,
                    "generated": False,
                    "completed": False,
                    "stars_earned": 0,
                    "effective_stars": 0,
                }
            elif quiz_record is None:
                quiz_state = {
                    "id": None,
                    "locked": False,
                    "generated": False,
                    "completed": False,
                    "stars_earned": 0,
                    "effective_stars": 0,
                }
            else:
                quiz_state = {
                    "id": quiz_record.id,
                    "locked": False,
                    "generated": True,
                    "completed": quiz_record.completed,
                    "stars_earned": quiz_record.stars_earned or 0,
                    "effective_stars": compute_effective_stars(quiz_record.stars_earned or 0),
                }

            sorted_lessons = sorted(lessons, key=lambda lesson: lesson.order_index)
            lesson_summaries = [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "difficulty": lesson.difficulty,
                    "order_index": lesson.order_index,
                    "locked": lock_states.get(lesson.id, True),
                    "completed": progress_by_lesson_id[lesson.id].completed
                    if lesson.id in progress_by_lesson_id
                    else False,
                    "stars_earned": progress_by_lesson_id[lesson.id].stars_earned
                    if lesson.id in progress_by_lesson_id
                    else 0,
                }
                for lesson in sorted_lessons
            ]

            chapter_responses.append(
                {
                    "id": chapter.id,
                    "title": chapter.title,
                    "order_index": chapter.order_index,
                    "quiz": quiz_state,
                    "lessons": lesson_summaries,
                }
            )

        return {"subject": subject, "chapters": chapter_responses}

    async def get_lesson(self, lesson_id: UUID) -> dict:
        lesson = await self.lesson_dao.get_lesson_by_id(lesson_id)
        if lesson is None:
            raise LessonNotFoundError(f"Lesson {lesson_id} not found")
        return {
            "id": lesson.id,
            "title": lesson.title,
            "difficulty": lesson.difficulty,
            "stars_available": lesson.stars_available or 3,
            "content": sanitize_lesson_content(lesson.content),
        }
