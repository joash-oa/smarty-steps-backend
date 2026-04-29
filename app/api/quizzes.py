from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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
    return QuizService(LessonDAO(db), ProgressDAO(db), get_claude_client())


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
    db: AsyncSession = Depends(get_db),
):
    progress_dao = ProgressDAO(db)
    quiz = await progress_dao.get_quiz_by_id(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz not found")

    svc = QuizService(LessonDAO(db), progress_dao, get_claude_client())
    learner_svc = LearnerService(LearnerDAO(db))
    learner_dao = LearnerDAO(db)

    result = await svc.submit_quiz(
        parent=parent,
        learner_id=quiz.learner_id,
        quiz_id=quiz_id,
        time_seconds=body.time_seconds,
        answers=body.answers,
        learner_svc=learner_svc,
        learner_dao=learner_dao,
    )
    return SubmitQuizResponse(**result)
