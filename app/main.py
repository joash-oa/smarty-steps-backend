from fastapi import FastAPI

from app.api import auth, health, learners

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(learners.router)
