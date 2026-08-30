from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.user import UserResponse


class MessageCreate(BaseModel):
    content: str = Field(min_length=2)


class MessageResponse(BaseModel):
    id: int
    ticket_id: int
    author_id: int
    author: UserResponse
    content: str

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
