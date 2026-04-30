from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.core.exceptions import LearnerNotFoundError, LearnerOwnershipError
from app.daos.learner_dao import LearnerDAO
from app.daos.lesson_dao import LessonDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Parent
from app.db.session import get_db
from app.schemas.curriculum import (
    ChapterResponse,
    CurriculumResponse,
    LessonDetailResponse,
    LessonSummary,
    QuizState,
)
from app.services.grading import compute_effective_stars
from app.services.learner_service import LearnerService
from app.services.lesson_service import (
    compute_lock_states,
    sanitize_lesson_content,
)

VALID_SUBJECTS = {"math", "science", "english"}

router = APIRouter(tags=["curriculum"])


@router.get("/subjects/{subject}/chapters", response_model=CurriculumResponse)
async def get_curriculum(
    subject: str,
    learner_id: UUID = Query(...),
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    if subject not in VALID_SUBJECTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid subject. Must be one of {VALID_SUBJECTS}",
        )

    lesson_dao = LessonDAO(db)
    progress_dao = ProgressDAO(db)

    try:
        learner = await LearnerService(LearnerDAO(db)).get(parent, learner_id)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )

    chapters = await lesson_dao.get_chapters_by_subject(subject)
    all_progress = await progress_dao.get_all_progress_for_learner(learner.id)
    completed_lesson_ids = {p.lesson_id for p in all_progress if p.completed}
    progress_by_lesson_id = {p.lesson_id: p for p in all_progress}

    lessons_by_chapter = {
        chapter.id: await lesson_dao.get_lessons_by_chapter(chapter.id) for chapter in chapters
    }
    lock_states = compute_lock_states(
        chapters=chapters,
        lessons_by_chapter=lessons_by_chapter,
        completed_lesson_ids=completed_lesson_ids,
    )

    chapter_responses = []
    for chapter in chapters:
        lessons = lessons_by_chapter.get(chapter.id, [])
        quiz_record = await progress_dao.get_chapter_quiz(learner.id, chapter.id)
        all_lessons_complete = (
            all(lesson.id in completed_lesson_ids for lesson in lessons) if lessons else False
        )

        if not lessons or not all_lessons_complete:
            quiz_state = QuizState(locked=True, generated=False)
        elif quiz_record is None:
            quiz_state = QuizState(locked=False, generated=False)
        else:
            quiz_state = QuizState(
                id=quiz_record.id,
                locked=False,
                generated=True,
                completed=quiz_record.completed,
                stars_earned=quiz_record.stars_earned or 0,
                effective_stars=compute_effective_stars(quiz_record.stars_earned or 0),
            )

        sorted_lessons = sorted(lessons, key=lambda lesson: lesson.order_index)
        lesson_summaries = [
            LessonSummary(
                id=lesson.id,
                title=lesson.title,
                difficulty=lesson.difficulty,
                order_index=lesson.order_index,
                locked=lock_states.get(lesson.id, True),
                completed=progress_by_lesson_id[lesson.id].completed
                if lesson.id in progress_by_lesson_id
                else False,
                stars_earned=progress_by_lesson_id[lesson.id].stars_earned
                if lesson.id in progress_by_lesson_id
                else 0,
            )
            for lesson in sorted_lessons
        ]

        chapter_responses.append(
            ChapterResponse(
                id=chapter.id,
                title=chapter.title,
                order_index=chapter.order_index,
                quiz=quiz_state,
                lessons=lesson_summaries,
            )
        )

    return CurriculumResponse(subject=subject, chapters=chapter_responses)


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    lesson = await LessonDAO(db).get_lesson_by_id(lesson_id)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return LessonDetailResponse(
        id=lesson.id,
        title=lesson.title,
        difficulty=lesson.difficulty,
        stars_available=lesson.stars_available or 3,
        content=sanitize_lesson_content(lesson.content),
    )
