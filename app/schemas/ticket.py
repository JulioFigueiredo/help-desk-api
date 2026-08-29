from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import TicketPriority, TicketStatus
from app.schemas.category import CategoryResponse
from app.schemas.user import UserResponse


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    category_id: int = Field(gt=0)
    priority: TicketPriority = TicketPriority.MEDIUM


class TicketUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    category_id: int | None = Field(default=None, gt=0)


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: TicketStatus
    priority: TicketPriority
    customer_id: int
    agent_id: int | None
    category_id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None

    model_config = {"from_attributes": True}


class TicketDetailResponse(TicketResponse):
    customer: UserResponse
    agent: UserResponse | None = None
    category: CategoryResponse


class TicketAssign(BaseModel):
    agent_id: int | None = Field(default=None, gt=0)
