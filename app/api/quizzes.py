from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.clients.claude_client import get_claude_client
from app.daos.learner_dao import LearnerDAO
from app.daos.lesson_dao import LessonDAO
from app.daos.progress_dao import ProgressDAO
from app.db.models import Parent
from app.db.session import get_db
from app.schemas.quiz import (
    CheckQuizAnswerRequest,
    CheckQuizAnswerResponse,
    QuizDetailResponse,
    SubmitQuizRequest,
    SubmitQuizResponse,
)
from app.services.learner_service import LearnerService
from app.services.quiz_service import QuizService

router = APIRouter(prefix="/chapter-quizzes", tags=["quizzes"])


def _svc(db: AsyncSession = Depends(get_db)) -> QuizService:
    return QuizService(LessonDAO(db), ProgressDAO(db), get_claude_client(), LearnerDAO(db))


@router.get("/{quiz_id}", response_model=QuizDetailResponse)
async def get_quiz(quiz_id: UUID, svc: QuizService = Depends(_svc)):
    result = await svc.get_quiz(quiz_id)
    return QuizDetailResponse(**result)


@router.post("/{quiz_id}/check-answer", response_model=CheckQuizAnswerResponse)
async def check_quiz_answer(
    quiz_id: UUID,
    body: CheckQuizAnswerRequest,
    svc: QuizService = Depends(_svc),
):
    result = await svc.check_quiz_answer(quiz_id, body.exercise_id, body.answer)
    return CheckQuizAnswerResponse(**result)


@router.post("/{quiz_id}/submit", response_model=SubmitQuizResponse)
async def submit_quiz(
    quiz_id: UUID,
    body: SubmitQuizRequest,
    parent: Parent = Depends(get_current_parent),
    svc: QuizService = Depends(_svc),
    db: AsyncSession = Depends(get_db),
):
    learner_svc = LearnerService(LearnerDAO(db))
    result = await svc.submit_quiz(
        parent=parent,
        quiz_id=quiz_id,
        time_seconds=body.time_seconds,
        answers=body.answers,
        learner_svc=learner_svc,
    )
    return SubmitQuizResponse(**result)
