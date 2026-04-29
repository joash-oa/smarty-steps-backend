from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_parent, get_current_parent_dashboard
from app.core.exceptions import InvalidPinError, LearnerNotFoundError, LearnerOwnershipError
from app.daos.dashboard_dao import DashboardDAO
from app.daos.learner_dao import LearnerDAO
from app.db.models import Parent
from app.db.session import get_db
from app.schemas.dashboard import DashboardStatsResponse
from app.schemas.parent import ParentTokenResponse, VerifyPinRequest
from app.services.dashboard_service import DashboardService
from app.services.learner_service import LearnerService
from app.services.parent_service import ParentService

router = APIRouter(prefix="/parent", tags=["parent"])


@router.post("/verify-pin", response_model=ParentTokenResponse)
async def verify_pin(
    body: VerifyPinRequest,
    parent: Parent = Depends(get_current_parent),
):
    try:
        token = ParentService().verify_pin_and_issue_token(parent, body.pin)
    except InvalidPinError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect PIN")
    return ParentTokenResponse(token=token)


@router.get("/learners/{learner_id}/stats", response_model=DashboardStatsResponse)
async def get_learner_stats(
    learner_id: UUID,
    parent: Parent = Depends(get_current_parent_dashboard),
    db: AsyncSession = Depends(get_db),
):
    learner_svc = LearnerService(LearnerDAO(db))
    svc = DashboardService(DashboardDAO(db))
    try:
        result = await svc.get_stats(parent, learner_id, learner_svc)
    except LearnerNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Learner not found")
    except LearnerOwnershipError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return DashboardStatsResponse(
        time_per_subject=result["time_per_subject"],
        mastered=result["mastered"],
        needs_practice=result["needs_practice"],
        recent_activity=result["recent_activity"],
    )
