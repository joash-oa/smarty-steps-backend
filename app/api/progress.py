from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.core.enums import Subject
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


@router.post("/lessons/{lesson_id}/check-answer", response_model=CheckAnswerResponse)
async def check_lesson_answer(
    lesson_id: UUID,
    body: CheckAnswerRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProgressService(LessonDAO(db), ProgressDAO(db), LearnerDAO(db))
    result = await svc.check_lesson_answer(lesson_id, body.exercise_id, body.answer)
    return CheckAnswerResponse(**result)


@router.post("/learners/{learner_id}/progress", response_model=SubmitLessonResponse)
async def submit_lesson(
    learner_id: UUID,
    body: SubmitLessonRequest,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    svc = ProgressService(LessonDAO(db), ProgressDAO(db), LearnerDAO(db))
    learner_svc = LearnerService(LearnerDAO(db))
    result = await svc.submit_lesson(
        parent=parent,
        learner_id=learner_id,
        lesson_id=body.lesson_id,
        time_seconds=body.time_seconds,
        answers=body.answers,
        learner_svc=learner_svc,
    )
    return SubmitLessonResponse(**result)


@router.get("/learners/{learner_id}/progress", response_model=ProgressSummaryResponse)
async def get_progress_summary(
    learner_id: UUID,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    svc = ProgressService(LessonDAO(db), ProgressDAO(db), LearnerDAO(db))
    learner_svc = LearnerService(LearnerDAO(db))
    result = await svc.get_summary(parent, learner_id, learner_svc)
    return ProgressSummaryResponse(**result)


@router.get("/learners/{learner_id}/progress/{subject}", response_model=SubjectProgressResponse)
async def get_subject_progress(
    learner_id: UUID,
    subject: Subject,
    parent: Parent = Depends(get_current_parent),
    db: AsyncSession = Depends(get_db),
):
    svc = ProgressService(LessonDAO(db), ProgressDAO(db), LearnerDAO(db))
    learner_svc = LearnerService(LearnerDAO(db))
    result = await svc.get_subject_progress(parent, learner_id, subject, learner_svc)
    return SubjectProgressResponse(**result)
