import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import auth, curriculum, health, learners, parent, progress, quizzes

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    asyncio.create_task(_maybe_sync_standards())
    yield


async def _maybe_sync_standards() -> None:
    from app.clients.claude_client import get_claude_client
    from app.clients.standards_api import StandardsAPIClient
    from app.daos.lesson_dao import LessonDAO
    from app.db.session import AsyncSessionLocal
    from app.services.content_service import GRADE_LEVELS, SUBJECTS, ContentService

    async with AsyncSessionLocal() as session:
        count = await LessonDAO(session).count_standards()
        if count > 0:
            return

    logger.info("Standards table empty — starting background content sync")
    for subject in SUBJECTS:
        for grade_level in GRADE_LEVELS:
            async with AsyncSessionLocal() as session:
                async with session.begin():
                    service = ContentService(
                        lesson_dao=LessonDAO(session),
                        standards_api=StandardsAPIClient(),
                        claude=get_claude_client(),
                    )
                    await service.sync_subject_grade(subject, grade_level)
    logger.info("Background content sync complete")


app = FastAPI(title="Smarty Steps", lifespan=lifespan)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
app.include_router(parent.router)
app.include_router(curriculum.router)
app.include_router(progress.router)
app.include_router(quizzes.router)
