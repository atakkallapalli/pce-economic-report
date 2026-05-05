import uuid

from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository
from app.schemas.user import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.user_repo = UserRepository(db)

    async def register(self, data: UserRegisterRequest) -> tuple[UserResponse, TokenResponse]:
        existing = await self.user_repo.get_by_email(data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )

        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            full_name=data.full_name,
            role=UserRole.MEMBER,
        )
        user = await self.user_repo.create(user)

        tokens = self._create_tokens(user)
        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return UserResponse.model_validate(user), tokens

    async def login(self, data: UserLoginRequest) -> tuple[UserResponse, TokenResponse]:
        user = await self.user_repo.get_by_email(data.email)
        if not user or not verify_password(data.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated",
            )

        tokens = self._create_tokens(user)
        logger.info("user_logged_in", user_id=str(user.id))
        return UserResponse.model_validate(user), tokens

    async def refresh_token(self, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )

        return self._create_tokens(user)

    async def get_current_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(user)

    def _create_tokens(self, user: User) -> TokenResponse:
        token_data = {"sub": str(user.id), "role": user.role.value}
        return TokenResponse(
            access_token=create_access_token(token_data),
            refresh_token=create_refresh_token(token_data),
        )
