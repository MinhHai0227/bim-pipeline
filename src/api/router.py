from fastapi import APIRouter, HTTPException

from src.db.session import ping_database

api_router = APIRouter()


@api_router.get("/health", tags=["health"])
def health_check():
    return {"status": "ok"}


@api_router.get("/health/db", tags=["health"])
def database_health_check():
    try:
        ping_database()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "database": "unavailable",
                "message": str(exc),
            },
        ) from exc

    return {"status": "ok", "database": "connected"}
