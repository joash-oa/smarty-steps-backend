from fastapi import FastAPI
from app.api import health, auth

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
app.include_router(auth.router)
