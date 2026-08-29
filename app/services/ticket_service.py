from fastapi import HTTPException, status

from app.models import Ticket, User
from app.models.enums import TicketPriority, TicketStatus, UserRole
from app.repositories.category_repo import CategoryRepository
from app.repositories.ticket_repo import TicketRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.ticket import TicketCreate, TicketResponse


class TicketService:
    def __init__(
        self, ticket_repo: TicketRepository, category_repo: CategoryRepository
    ):
        self.ticket_repo = ticket_repo
        self.category_repo = category_repo

    async def create_ticket(self, data: TicketCreate, current_user: User) -> Ticket:
        """Create a new ticket ensuring category existence and customer ownership."""
        category = await self.category_repo.get_by_id(data.category_id)

        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )

        ticket = Ticket(**data.model_dump(), customer_id=current_user.id)

        return await self.ticket_repo.create(ticket)

    async def get_ticket(self, ticket_id: int, current_user: User) -> Ticket:
        """Retrieve ticket by ID ensuring RBAC authorization."""
        ticket = await self.ticket_repo.get_by_id(ticket_id)

        if not ticket:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Ticket not found",
            )

        if (
            current_user.role == UserRole.CUSTOMER
            and ticket.customer_id != current_user.id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )

        return ticket

    async def list_tickets(
        self,
        current_user: User,
        page: int = 1,
        limit: int = 20,
        customer_id: int | None = None,
        agent_id: int | None = None,
        category_id: int | None = None,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        sort: str = "-created_at",
    ) -> PaginatedResponse[TicketResponse]:
        """List tickets with pagination, filters, and customer tenant isolation."""
        if current_user.role == UserRole.CUSTOMER:
            customer_id = current_user.id

        tickets, total = await self.ticket_repo.list_tickets(
            page=page,
            limit=limit,
            customer_id=customer_id,
            agent_id=agent_id,
            category_id=category_id,
            status=status,
            priority=priority,
            sort=sort,
        )

        return PaginatedResponse.create(
            items=tickets,
            total=total,
            page=page,
            limit=limit,
        )
