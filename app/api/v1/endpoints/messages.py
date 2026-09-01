from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models import User
from app.repositories.message_repo import MessageRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.message import MessageCreate, MessageResponse
from app.services.message_service import MessageService

router = APIRouter()


def get_message_service(db: AsyncSession = Depends(get_db)) -> MessageService:
    return MessageService(
        message_repo=MessageRepository(db), ticket_repo=TicketRepository(db)
    )


@router.post(
    "/{ticket_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_message(
    ticket_id: int,
    data: MessageCreate,
    current_user: User = Depends(get_current_active_user),
    service: MessageService = Depends(get_message_service),
):
    return await service.create_message(ticket_id, data, current_user)


@router.get(
    "/{ticket_id}/messages",
    response_model=list[MessageResponse],
    status_code=status.HTTP_200_OK,
)
async def list_messages(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    service: MessageService = Depends(get_message_service),
):
    return await service.list_messages(ticket_id, current_user)
