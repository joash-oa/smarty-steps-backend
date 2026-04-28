from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import Parent


class ParentDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, cognito_id: str, email: str, pin_hash: str) -> Parent:
        parent = Parent(cognito_id=cognito_id, email=email, pin_hash=pin_hash)
        self.session.add(parent)
        await self.session.flush()
        await self.session.refresh(parent)
        return parent

    async def get_by_cognito_id(self, cognito_id: str) -> Parent | None:
        result = await self.session.execute(
            select(Parent).where(Parent.cognito_id == cognito_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Parent | None:
        result = await self.session.execute(
            select(Parent).where(Parent.email == email)
        )
        return result.scalar_one_or_none()
