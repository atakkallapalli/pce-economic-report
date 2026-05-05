from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=dict,
    status_code=201,
    summary="Register a new user",
    description="Create a new user account and receive JWT tokens.",
)
async def register(
    data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user with email, password, and full name."""
    service = AuthService(db)
    user, tokens = await service.register(data)
    return {"user": user.model_dump(), "tokens": tokens.model_dump()}


@router.post(
    "/login",
    response_model=dict,
    summary="Login",
    description="Authenticate with email and password to receive JWT tokens.",
)
async def login(
    data: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with email and password to receive access and refresh tokens."""
    service = AuthService(db)
    user, tokens = await service.login(data)
    return {"user": user.model_dump(), "tokens": tokens.model_dump()}


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh token",
    description="Get a new access token using a valid refresh token.",
)
async def refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for new access and refresh tokens."""
    service = AuthService(db)
    return await service.refresh_token(data.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
    description="Get the profile of the currently authenticated user.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user's profile."""
    service = AuthService(db)
    return await service.get_current_user(current_user.id)
