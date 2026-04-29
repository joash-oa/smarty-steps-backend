from fastapi import APIRouter, Depends

from app.api.deps import get_current_parent
from app.db.models import Parent
from app.schemas.parent import ParentTokenResponse, VerifyPinRequest
from app.services.parent_service import ParentService

router = APIRouter(prefix="/parent", tags=["parent"])


@router.post("/verify-pin", response_model=ParentTokenResponse)
async def verify_pin(
    body: VerifyPinRequest,
    parent: Parent = Depends(get_current_parent),
):
    token = ParentService().verify_pin_and_issue_token(parent, body.pin)
    return ParentTokenResponse(token=token)
