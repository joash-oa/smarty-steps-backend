from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.core.enums import Subject
from app.core.exceptions import (
    ExerciseNotFoundError,
    IncompleteAnswersError,
    LearnerNotFoundError,
    LearnerOwnershipError,
    LessonNotFoundError,
)
from app.daos.learner_dao import LearnerDAO
from app.daos.lesson_dao import LessonDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Parent
from app.db.session import get_db
from app.schemas.progress import (
    CheckAnswerRequest,
    CheckAnswerResponse,
    ProgressSummaryResponse,
    SubjectProgressResponse,
    SubmitLessonRequest,
    SubmitLessonResponse,
)
from app.services.learner_service import LearnerService
from app.services.progress_service import ProgressService

router = APIRouter(tags=["progress"])


def _progress_service(db: AsyncSession = Depends(get_db)) -> ProgressService:
    return ProgressService(LessonDAO(db), ProgressDAO(db), LearnerDAO(db))


def _learner_service(db: AsyncSession = Depends(get_db)) -> LearnerService:
    return LearnerService(LearnerDAO(db))


@router.post("/lessons/{lesson_id}/check-answer", response_model=CheckAnswerResponse)
async def check_lesson_answer(
    lesson_id: UUID,
    body: CheckAnswerRequest,
    svc: ProgressService = Depends(_progress_service),
):
    try:
        result = await svc.check_lesson_answer(lesson_id, body.exercise_id, body.answer)
    except LessonNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    except ExerciseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return CheckAnswerResponse(**result)


@router.post("/learners/{learner_id}/progress", response_model=SubmitLessonResponse)
async def submit_lesson(
    learner_id: UUID,
    body: SubmitLessonRequest,
    parent: Parent = Depends(get_current_parent),
    svc: ProgressService = Depends(_progress_service),
    learner_svc: LearnerService = Depends(_learner_service),
):
    try:
        result = await svc.submit_lesson(
            parent=parent,
            learner_id=learner_id,
            lesson_id=body.lesson_id,
            time_seconds=body.time_seconds,
            answers=body.answers,
            learner_svc=learner_svc,
        )
    except LessonNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )
    except IncompleteAnswersError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing answers for exercises: {exc.missing_exercise_ids}",
        )
    return SubmitLessonResponse(**result)


@router.get("/learners/{learner_id}/progress", response_model=ProgressSummaryResponse)
async def get_progress_summary(
    learner_id: UUID,
    parent: Parent = Depends(get_current_parent),
    svc: ProgressService = Depends(_progress_service),
    learner_svc: LearnerService = Depends(_learner_service),
):
    try:
        result = await svc.get_summary(parent, learner_id, learner_svc)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )
    return ProgressSummaryResponse(**result)


@router.get("/learners/{learner_id}/progress/{subject}", response_model=SubjectProgressResponse)
async def get_subject_progress(
    learner_id: UUID,
    subject: Subject,
    parent: Parent = Depends(get_current_parent),
    svc: ProgressService = Depends(_progress_service),
    learner_svc: LearnerService = Depends(_learner_service),
):
    try:
        result = await svc.get_subject_progress(parent, learner_id, subject, learner_svc)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )
    return SubjectProgressResponse(**result)
