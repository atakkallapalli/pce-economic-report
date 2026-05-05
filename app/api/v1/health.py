from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.core.logging import get_logger
from app.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])
logger = get_logger(__name__)


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check the health status of the API and its dependencies.",
)
async def health_check():
    """Basic health check endpoint for load balancer integration."""
    db_status = "healthy"
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    redis_status = "healthy"
    try:
        from app.core.redis import get_redis

        r = await get_redis()
        await r.ping()
    except Exception:
        redis_status = "unavailable"

    rabbitmq_status = "healthy"
    try:
        from app.core.rabbitmq import get_rabbitmq_channel

        await get_rabbitmq_channel()
    except Exception:
        rabbitmq_status = "unavailable"

    overall = "healthy"
    if db_status == "unhealthy":
        overall = "degraded"

    return HealthResponse(
        status=overall,
        database=db_status,
        redis=redis_status,
        rabbitmq=rabbitmq_status,
    )


@router.get(
    "/health/ready",
    summary="Readiness check",
    description="Check if the application is ready to serve traffic.",
)
async def readiness_check():
    """Readiness probe for Kubernetes."""
    return {"status": "ready", "app": settings.APP_NAME}
