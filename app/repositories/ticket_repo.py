from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import TicketPriority, TicketStatus
from app.models.ticket import Ticket


class TicketRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        await self.session.commit()
        await self.session.refresh(ticket)
        return ticket

    async def get_by_id(self, ticket_id: int) -> Ticket | None:
        """Fetch ticket by ID with eager loading of related entities.

        selectinload avoids MissingGreenlet errors when accessing customer,
        agent, or category in async execution contexts.
        """
        stmt = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.agent),
                selectinload(Ticket.category),
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tickets(
        self,
        page: int = 1,
        limit: int = 20,
        customer_id: int | None = None,
        agent_id: int | None = None,
        category_id: int | None = None,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        sort: str = "-created_at",
    ) -> tuple[list[Ticket], int]:
        """List tickets with dynamic filtering, secure sorting, and pagination.

        Returns:
            A tuple of (tickets_list, total_count).
        """
        # Declarative filter mapping
        filter_map = {
            Ticket.customer_id: customer_id,
            Ticket.agent_id: agent_id,
            Ticket.category_id: category_id,
            Ticket.status: status,
            Ticket.priority: priority,
        }
        conditions = [
            column == value for column, value in filter_map.items() if value is not None
        ]

        # Total count query using the same filtered conditions
        count_stmt = select(func.count(Ticket.id)).where(*conditions)
        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        # Whitelist for sortable columns to prevent invalid attributes or injection
        sort_fields = {
            "created_at": Ticket.created_at,
            "updated_at": Ticket.updated_at,
            "priority": Ticket.priority,
        }

        descending = sort.startswith("-")
        field_name = sort.lstrip("-")
        column = sort_fields.get(field_name, Ticket.created_at)
        order_clause = column.desc() if descending else column.asc()

        # Pagination offset and limit
        offset = max(0, (page - 1) * limit)
        stmt = (
            select(Ticket)
            .where(*conditions)
            .order_by(order_clause)
            .offset(offset)
            .limit(limit)
            .options(
                selectinload(Ticket.customer),
                selectinload(Ticket.agent),
                selectinload(Ticket.category),
            )
        )

        result = await self.session.execute(stmt)
        tickets = list(result.scalars().all())

        return tickets, total

    async def update(self, ticket: Ticket) -> Ticket:
        await self.session.commit()
        await self.session.refresh(ticket)

        return ticket
