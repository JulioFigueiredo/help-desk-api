from fastapi import HTTPException, status

from app.models import Category
from app.repositories.category_repo import CategoryRepository
from app.schemas.category import CategoryCreate


class CategoryService:
    def __init__(self, repo: CategoryRepository):
        self.repo = repo

    async def create_category(self, data: CategoryCreate) -> Category:
        existing = await self.repo.get_by_name(data.name)

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category already exists",
            )

        category = Category(name=data.name, description=data.description)
        return await self.repo.create(category)

    async def get_category(self, category_id: int) -> Category:
        category = await self.repo.get_by_id(category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        return category

    async def list_categories(self, skip: int = 0, limit: int = 100) -> list[Category]:
        return await self.repo.get_all(skip=skip, limit=limit)
