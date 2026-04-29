from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent
from app.core.exceptions import LearnerNotFoundError, LearnerOwnershipError
from app.daos.learner_dao import LearnerDAO
from app.db.models import Parent
from app.db.session import get_db
from app.schemas.learner import (
    CreateLearnerRequest,
    LearnerListResponse,
    LearnerResponse,
    UpdateLearnerRequest,
)
from app.services.learner_service import LearnerService

router = APIRouter(prefix="/learners", tags=["learners"])


def _svc(db: AsyncSession = Depends(get_db)) -> LearnerService:
    return LearnerService(LearnerDAO(db))


@router.post("", response_model=LearnerResponse, status_code=status.HTTP_201_CREATED)
async def create_learner(
    body: CreateLearnerRequest,
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    learner = await svc.create(
        parent=parent,
        name=body.name,
        age=body.age,
        grade_level=body.grade_level,
        avatar_emoji=body.avatar_emoji,
    )
    return LearnerResponse.model_validate(learner)


@router.get("", response_model=LearnerListResponse)
async def list_learners(
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    learners = await svc.list_for_parent(parent)
    return LearnerListResponse(
        learners=[LearnerResponse.model_validate(learner) for learner in learners]
    )


@router.get("/{learner_id}", response_model=LearnerResponse)
async def get_learner(
    learner_id: UUID,
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    try:
        learner = await svc.get(parent, learner_id)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )
    return LearnerResponse.model_validate(learner)


@router.patch("/{learner_id}", response_model=LearnerResponse)
async def update_learner(
    learner_id: UUID,
    body: UpdateLearnerRequest,
    parent: Parent = Depends(get_current_parent),
    svc: LearnerService = Depends(_svc),
):
    try:
        learner = await svc.update(
            parent=parent,
            learner_id=learner_id,
            name=body.name,
            avatar_emoji=body.avatar_emoji,
            grade_level=body.grade_level,
        )
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Learner not owned by parent"
        )
    return LearnerResponse.model_validate(learner)
