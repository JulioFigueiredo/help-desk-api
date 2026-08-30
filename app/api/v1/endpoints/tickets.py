from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user, require_staff
from app.db.session import get_db
from app.models import User
from app.models.enums import TicketPriority, TicketStatus
from app.repositories.category_repo import CategoryRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.user_repo import UserRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.ticket import (
    TicketAssign,
    TicketCreate,
    TicketDetailResponse,
    TicketResponse,
    TicketStatusUpdate,
)
from app.services.ticket_service import TicketService

router = APIRouter()


def get_ticket_service(db: AsyncSession = Depends(get_db)) -> TicketService:
    return TicketService(
        ticket_repo=TicketRepository(db),
        category_repo=CategoryRepository(db),
        user_repo=UserRepository(db),
    )


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(get_current_active_user),
    service: TicketService = Depends(get_ticket_service),
):
    return await service.create_ticket(data, current_user)


@router.get("/", response_model=PaginatedResponse[TicketResponse])
async def list_tickets(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    customer_id: int | None = Query(None, description="Filter by customer ID"),
    agent_id: int | None = Query(None, description="Filter by agent ID"),
    category_id: int | None = Query(None, description="Filter by category ID"),
    ticket_status: TicketStatus | None = Query(
        None, alias="status", description="Filter by status"
    ),
    priority: TicketPriority | None = Query(None, description="Filter by priority"),
    sort: str = Query("-created_at", description="Sort field (e.g. -created_at)"),
    current_user: User = Depends(get_current_active_user),
    service: TicketService = Depends(get_ticket_service),
):
    return await service.list_tickets(
        current_user=current_user,
        page=page,
        limit=limit,
        customer_id=customer_id,
        agent_id=agent_id,
        category_id=category_id,
        status=ticket_status,
        priority=priority,
        sort=sort,
    )


@router.get(
    "/{ticket_id}", response_model=TicketDetailResponse, status_code=status.HTTP_200_OK
)
async def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    service: TicketService = Depends(get_ticket_service),
):
    return await service.get_ticket(ticket_id, current_user)


@router.post(
    "/{ticket_id}/assign", response_model=TicketResponse, status_code=status.HTTP_200_OK
)
async def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    current_user: User = Depends(require_staff),
    service: TicketService = Depends(get_ticket_service),
):
    return await service.assign_ticket(ticket_id, data, current_user)


@router.patch(
    "/{ticket_id}/status", response_model=TicketResponse, status_code=status.HTTP_200_OK
)
async def change_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    current_user: User = Depends(require_staff),
    service: TicketService = Depends(get_ticket_service),
):

    return await service.change_status(ticket_id, data, current_user)
