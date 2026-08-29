from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user, get_db, require_admin
from app.models import User
from app.repositories.category_repo import CategoryRepository
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import CategoryService

router = APIRouter()


def get_category_service(db: AsyncSession = Depends(get_db)) -> CategoryService:
    return CategoryService(CategoryRepository(db))


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    data: CategoryCreate,
    service: CategoryService = Depends(get_category_service),
    _admin: User = Depends(require_admin),
):
    return await service.create_category(data)


@router.get("/", response_model=list[CategoryResponse])
async def get_all(
    skip: int = 0,
    limit: int = 100,
    service: CategoryService = Depends(get_category_service),
    _user: User = Depends(get_current_active_user),
):
    return await service.list_categories(skip=skip, limit=limit)


@router.get("/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: int,
    service: CategoryService = Depends(get_category_service),
    _user: User = Depends(get_current_active_user),
):
    return await service.get_category(category_id)
