from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from app.api.v1 import auth, comments, health, tasks, users
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rabbitmq import close_rabbitmq
from app.core.redis import close_redis
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.request_id import RequestIDMiddleware
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    setup_logging()
    yield
    await close_redis()
    await close_rabbitmq()


app = FastAPI(
    title="Task Management API",
    description=(
        "A RESTful API for managing tasks with assignment, workflow tracking, "
        "commenting, search, and notification capabilities."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.METRICS_ENABLED:
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

app.include_router(health.router)
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(tasks.router, prefix=settings.API_V1_PREFIX)
app.include_router(comments.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
