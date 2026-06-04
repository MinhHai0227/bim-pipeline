from fastapi import FastAPI

from src.api.router import api_router
from src.core.config import settings


app = FastAPI(
    title=settings.app_name,
    description="API for IFC parsing, validation, and BIM-to-digital-twin data workflows.",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api")


@app.get("/", tags=["health"])
def read_root():
    return {
        "message": "BIM Pipeline API is running",
        "docs": "/docs",
        "health": "/api/health",
        "database_health": "/api/health/db",
    }
