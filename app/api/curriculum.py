from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.core.enums import Subject
from app.core.exceptions import LearnerNotFoundError, LearnerOwnershipError, LessonNotFoundError
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
from app.services.curriculum_service import CurriculumService
from app.services.learner_service import LearnerService

router = APIRouter(tags=["curriculum"])


def _curriculum_service(db: AsyncSession = Depends(get_db)) -> CurriculumService:
    return CurriculumService(LessonDAO(db), ProgressDAO(db))


def _learner_service(db: AsyncSession = Depends(get_db)) -> LearnerService:
    return LearnerService(LearnerDAO(db))


@router.get("/subjects/{subject}/chapters", response_model=CurriculumResponse)
async def get_curriculum(
    subject: Subject,
    learner_id: UUID = Query(...),
    parent: Parent = Depends(get_current_parent),
    svc: CurriculumService = Depends(_curriculum_service),
    learner_svc: LearnerService = Depends(_learner_service),
):
    try:
        result = await svc.get_curriculum(parent, learner_id, subject, learner_svc)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )

    return CurriculumResponse(
        subject=result["subject"],
        chapters=[
            ChapterResponse(
                id=ch["id"],
                title=ch["title"],
                order_index=ch["order_index"],
                quiz=QuizState(**ch["quiz"]),
                lessons=[LessonSummary(**ls) for ls in ch["lessons"]],
            )
            for ch in result["chapters"]
        ],
    )


@router.get("/lessons/{lesson_id}", response_model=LessonDetailResponse)
async def get_lesson(
    lesson_id: UUID,
    svc: CurriculumService = Depends(_curriculum_service),
):
    try:
        result = await svc.get_lesson(lesson_id)
    except LessonNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    return LessonDetailResponse(**result)
