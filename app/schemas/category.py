from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = Field(default=None)


class CategoryResponse(BaseModel):
    id: int
    name: str
    description: str | None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
