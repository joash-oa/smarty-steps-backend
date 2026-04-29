from fastapi import FastAPI

from app.api import auth, curriculum, health, learners, parent

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
app.include_router(parent.router)
app.include_router(curriculum.router)
