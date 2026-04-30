from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.core.exceptions import (
    ExerciseNotFoundError,
    IncompleteAnswersError,
    LearnerNotFoundError,
    LearnerOwnershipError,
    QuizNotFoundError,
)
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


def _quiz_service(db: AsyncSession = Depends(get_db)) -> QuizService:
    return QuizService(LessonDAO(db), ProgressDAO(db), LearnerDAO(db))


def _learner_service(db: AsyncSession = Depends(get_db)) -> LearnerService:
    return LearnerService(LearnerDAO(db))


@router.get("/{quiz_id}", response_model=QuizDetailResponse)
async def get_quiz(quiz_id: UUID, svc: QuizService = Depends(_quiz_service)):
    try:
        result = await svc.get_quiz(quiz_id)
    except QuizNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found or not yet generated"
        )
    return QuizDetailResponse(**result)


@router.post("/{quiz_id}/check-answer", response_model=CheckQuizAnswerResponse)
async def check_quiz_answer(
    quiz_id: UUID,
    body: CheckQuizAnswerRequest,
    svc: QuizService = Depends(_quiz_service),
):
    try:
        result = await svc.check_quiz_answer(quiz_id, body.exercise_id, body.answer)
    except QuizNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    except ExerciseNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")
    return CheckQuizAnswerResponse(**result)


@router.post("/{quiz_id}/submit", response_model=SubmitQuizResponse)
async def submit_quiz(
    quiz_id: UUID,
    body: SubmitQuizRequest,
    parent: Parent = Depends(get_current_parent),
    svc: QuizService = Depends(_quiz_service),
    learner_svc: LearnerService = Depends(_learner_service),
):
    try:
        result = await svc.submit_quiz(
            parent=parent,
            quiz_id=quiz_id,
            time_seconds=body.time_seconds,
            answers=body.answers,
            learner_svc=learner_svc,
        )
    except QuizNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz not found")
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )
    except IncompleteAnswersError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing answers for: {exc.missing_exercise_ids}",
        )
    return SubmitQuizResponse(**result)
