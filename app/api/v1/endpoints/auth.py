from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.user import UserCreate, UserResponse
from app.services.auth_service import AuthService

router = APIRouter()


def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    repo = UserRepository(db)

    return AuthService(repo)


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    data: UserCreate,
    service: AuthService = Depends(get_auth_service),
):
    return await service.register(data)


@router.post("/login", response_model=TokenResponse, status_code=200)
async def login(data: LoginRequest, service: AuthService = Depends(get_auth_service)):
    return await service.authenticate(data)


@router.post("/refresh", response_model=TokenResponse, status_code=200)
async def refresh(
    data: RefreshTokenRequest, service: AuthService = Depends(get_auth_service)
):
    return await service.refresh(data)
