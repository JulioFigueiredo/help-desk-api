from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user, get_db, require_admin
from app.models.user import User
from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    repo = UserRepository(db)
    return UserService(repo)


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user


@router.get("/", response_model=list[UserResponse])
async def get_all(
    _admin: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
    skip: int = 0,
    limit: int = 100,
):
    return await service.list_users(skip=skip, limit=limit)


@router.post("/", response_model=UserResponse, status_code=201)
async def create_user(
    data: UserCreate,
    _admin: User = Depends(require_admin),
    service: UserService = Depends(get_user_service),
):
    return await service.create_user(data)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
):
    return await service.get_user(user_id, current_user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    service: UserService = Depends(get_user_service),
):
    return await service.update_user(user_id, data, current_user)
