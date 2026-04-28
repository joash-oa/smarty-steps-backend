from fastapi import FastAPI
from app.api import health

app = FastAPI(title="Smarty Steps")

app.include_router(health.router)
