from fastapi import HTTPException, status

from app.models import Message, Ticket, User
from app.models.enums import TicketStatus, UserRole
from app.repositories.message_repo import MessageRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.message import MessageCreate


class MessageService:
    def __init__(self, message_repo: MessageRepository, ticket_repo: TicketRepository):
        self.message_repo = message_repo
        self.ticket_repo = ticket_repo

    async def _get_ticket_or_fail(self, ticket_id: int) -> Ticket:
        ticket = await self.ticket_repo.get_by_id(ticket_id)

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )

        return ticket

    async def create_message(
        self, ticket_id: int, data: MessageCreate, current_user: User
    ) -> Message:
        ticket = await self._get_ticket_or_fail(ticket_id)

        if (
            current_user.role == UserRole.CUSTOMER
            and ticket.customer_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )

        if ticket.status == TicketStatus.CLOSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Ticket is closed"
            )

        message = Message(
            **data.model_dump(), ticket_id=ticket_id, author_id=current_user.id
        )

        return await self.message_repo.create(message)

    async def list_messages(self, ticket_id: int, current_user: User) -> list[Message]:
        ticket = await self._get_ticket_or_fail(ticket_id)

        if (
            current_user.role == UserRole.CUSTOMER
            and ticket.customer_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )

        return await self.message_repo.list_by_ticket(ticket_id)
