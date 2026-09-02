from datetime import timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_refresh_token
from app.models.enums import TicketPriority, TicketStatus, UserRole
from app.models.ticket import Ticket
from app.repositories.category_repo import CategoryRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.ticket_repo import TicketRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RefreshTokenRequest
from app.schemas.category import CategoryCreate
from app.schemas.message import MessageCreate
from app.schemas.ticket import (
    TicketAssign,
    TicketCreate,
    TicketPriorityUpdate,
    TicketStatusUpdate,
)
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import AuthService
from app.services.category_service import CategoryService
from app.services.message_service import MessageService
from app.services.ticket_service import TicketService
from app.services.ticket_state_machine import TicketStateMachine
from app.services.user_service import UserService

# --- Auth Service Tests ---


@pytest.mark.asyncio
async def test_auth_service_register_conflict(db_session: AsyncSession, customer_user):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.register(
            UserCreate(
                name="Duplicate",
                email=customer_user.email,
                password="password123",
            )
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_auth_service_register_success(db_session: AsyncSession):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    new_user = await service.register(
        UserCreate(
            name="Brand New",
            email="brandnew@example.com",
            password="password12345",
        )
    )
    assert new_user.id is not None
    assert new_user.email == "brandnew@example.com"
    assert new_user.role == UserRole.CUSTOMER


@pytest.mark.asyncio
async def test_auth_service_authenticate_success(
    db_session: AsyncSession, user_factory
):
    user = await user_factory(
        email="auth_success@example.com", password="mypassword123"
    )
    repo = UserRepository(db_session)
    service = AuthService(repo)

    tokens = await service.authenticate(
        LoginRequest(email=user.email, password="mypassword123")
    )
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None


@pytest.mark.asyncio
async def test_auth_service_authenticate_wrong_password(
    db_session: AsyncSession, customer_user
):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.authenticate(
            LoginRequest(email=customer_user.email, password="wrongpassword")
        )
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_service_authenticate_inactive_user(
    db_session: AsyncSession, inactive_user
):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.authenticate(
            LoginRequest(
                email=inactive_user.email,
                password="securepassword123",
            )
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_auth_service_refresh_success(db_session: AsyncSession, customer_user):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    rf_token = create_refresh_token(subject=customer_user.id)
    tokens = await service.refresh(RefreshTokenRequest(refresh_token=rf_token))
    assert tokens.access_token is not None
    assert tokens.refresh_token is not None


@pytest.mark.asyncio
async def test_auth_service_refresh_user_not_found(db_session: AsyncSession):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    rf_token = create_refresh_token(subject=99999)
    with pytest.raises(HTTPException) as exc:
        await service.refresh(RefreshTokenRequest(refresh_token=rf_token))
    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_service_refresh_inactive_user(
    db_session: AsyncSession, inactive_user
):
    repo = UserRepository(db_session)
    service = AuthService(repo)

    rf_token = create_refresh_token(subject=inactive_user.id)
    with pytest.raises(HTTPException) as exc:
        await service.refresh(RefreshTokenRequest(refresh_token=rf_token))
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_auth_service_refresh_invalid_sub(db_session: AsyncSession):
    import jwt

    from app.core.config import settings

    repo = UserRepository(db_session)
    service = AuthService(repo)

    token = jwt.encode(
        {"sub": "not-an-int", "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    with pytest.raises(HTTPException) as exc:
        await service.refresh(RefreshTokenRequest(refresh_token=token))
    assert exc.value.status_code == 401


# --- User Service Tests ---


@pytest.mark.asyncio
async def test_user_service_create_success(db_session: AsyncSession):
    repo = UserRepository(db_session)
    service = UserService(repo)

    user = await service.create_user(
        UserCreate(
            name="Created User",
            email="created@example.com",
            password="password123",
        )
    )
    assert user.id is not None
    assert user.name == "Created User"


@pytest.mark.asyncio
async def test_user_service_create_conflict(db_session: AsyncSession, customer_user):
    repo = UserRepository(db_session)
    service = UserService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.create_user(
            UserCreate(
                name="Another User",
                email=customer_user.email,
                password="password123",
            )
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_user_service_get_user_forbidden(
    db_session: AsyncSession, customer_user, agent_user
):
    repo = UserRepository(db_session)
    service = UserService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.get_user(user_id=agent_user.id, current_user=customer_user)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_user_service_get_user_not_found(db_session: AsyncSession, admin_user):
    repo = UserRepository(db_session)
    service = UserService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.get_user(user_id=99999, current_user=admin_user)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_user_service_update_same_email(db_session: AsyncSession, customer_user):
    repo = UserRepository(db_session)
    service = UserService(repo)

    updated = await service.update_user(
        user_id=customer_user.id,
        data=UserUpdate(name="Same Email Name", email=customer_user.email),
        current_user=customer_user,
    )
    assert updated.name == "Same Email Name"
    assert updated.email == customer_user.email


@pytest.mark.asyncio
async def test_user_service_update_conflict_email(
    db_session: AsyncSession, customer_user, agent_user
):
    repo = UserRepository(db_session)
    service = UserService(repo)

    with pytest.raises(HTTPException) as exc:
        await service.update_user(
            user_id=customer_user.id,
            data=UserUpdate(email=agent_user.email),
            current_user=customer_user,
        )
    assert exc.value.status_code == 409


@pytest.mark.asyncio
async def test_user_repo_delete_and_get_all(db_session: AsyncSession, user_factory):
    repo = UserRepository(db_session)
    u1 = await user_factory(email="u1@test.com")
    u2 = await user_factory(email="u2@test.com")

    all_users = await repo.get_all(skip=0, limit=10)
    assert len(all_users) >= 2
    assert u2.id in [u.id for u in all_users]

    await repo.delete(u1)
    found = await repo.get_by_id(u1.id)
    assert found is None


# --- Category Service & Repository Tests ---


@pytest.mark.asyncio
async def test_category_service_create_and_get(
    db_session: AsyncSession, sample_category
):
    repo = CategoryRepository(db_session)
    service = CategoryService(repo)

    cat = await service.create_category(
        CategoryCreate(name="New Cat", description="New Desc")
    )
    assert cat.id is not None
    assert cat.name == "New Cat"

    # Duplicate name raises 409
    with pytest.raises(HTTPException) as exc_dup:
        await service.create_category(CategoryCreate(name="New Cat"))
    assert exc_dup.value.status_code == 409

    # Get by ID
    fetched = await service.get_category(cat.id)
    assert fetched.id == cat.id

    # Get by non-existent ID raises 404
    with pytest.raises(HTTPException) as exc_404:
        await service.get_category(99999)
    assert exc_404.value.status_code == 404

    # List categories
    all_cats = await service.list_categories(skip=0, limit=10)
    assert len(all_cats) >= 2

    # Repo get_by_name
    by_name = await repo.get_by_name("New Cat")
    assert by_name is not None
    assert by_name.id == cat.id


# --- Message Service Tests ---


@pytest.mark.asyncio
async def test_message_service_crud_and_rbac(
    db_session: AsyncSession,
    customer_user,
    agent_user,
    user_factory,
    sample_category,
):
    msg_repo = MessageRepository(db_session)
    ticket_repo = TicketRepository(db_session)
    service = MessageService(msg_repo, ticket_repo)

    # 1. Ticket not found -> 404
    with pytest.raises(HTTPException) as exc_nf:
        await service.create_message(
            ticket_id=99999,
            data=MessageCreate(content="Testing ticket not found"),
            current_user=customer_user,
        )
    assert exc_nf.value.status_code == 404

    with pytest.raises(HTTPException) as exc_nf_list:
        await service.list_messages(ticket_id=99999, current_user=customer_user)
    assert exc_nf_list.value.status_code == 404

    # 2. Create ticket
    ticket = Ticket(
        title="Message Test Ticket",
        description="Testing message service",
        category_id=sample_category.id,
        customer_id=customer_user.id,
    )
    await ticket_repo.create(ticket)

    # 3. Create message - forbidden for stranger customer
    other_cust = await user_factory(email="stranger_msg@test.com")
    with pytest.raises(HTTPException) as exc_forbid:
        await service.create_message(
            ticket_id=ticket.id,
            data=MessageCreate(content="Forbidden message"),
            current_user=other_cust,
        )
    assert exc_forbid.value.status_code == 403

    # 4. Create message - success customer & agent
    msg1 = await service.create_message(
        ticket_id=ticket.id,
        data=MessageCreate(content="Hello from customer"),
        current_user=customer_user,
    )
    assert msg1.id is not None
    assert msg1.content == "Hello from customer"

    msg2 = await service.create_message(
        ticket_id=ticket.id,
        data=MessageCreate(content="Hello from agent"),
        current_user=agent_user,
    )
    assert msg2.id is not None

    # 5. List messages - forbidden for stranger
    with pytest.raises(HTTPException) as exc_list_forbid:
        await service.list_messages(ticket_id=ticket.id, current_user=other_cust)
    assert exc_list_forbid.value.status_code == 403

    # 6. List messages - success
    msgs = await service.list_messages(ticket_id=ticket.id, current_user=customer_user)
    assert len(msgs) == 2

    # 7. Closed ticket message rejection -> 400
    ticket.status = TicketStatus.CLOSED
    await ticket_repo.update(ticket)
    with pytest.raises(HTTPException) as exc_closed:
        await service.create_message(
            ticket_id=ticket.id,
            data=MessageCreate(content="Closed ticket msg"),
            current_user=customer_user,
        )
    assert exc_closed.value.status_code == 400


# --- Ticket Service Tests ---


@pytest.mark.asyncio
async def test_ticket_service_edge_cases(
    db_session: AsyncSession,
    customer_user,
    agent_user,
    admin_user,
    user_factory,
    sample_category,
):
    ticket_repo = TicketRepository(db_session)
    category_repo = CategoryRepository(db_session)
    user_repo = UserRepository(db_session)
    service = TicketService(ticket_repo, category_repo, user_repo)

    # 1. Ticket not found in _get_ticket_or_fail -> 404
    with pytest.raises(HTTPException) as exc_nf:
        await service.get_ticket(99999, current_user=customer_user)
    assert exc_nf.value.status_code == 404

    # 2. Reopen RESOLVED -> IN_PROGRESS
    ticket = await service.create_ticket(
        TicketCreate(
            title="Reopen Ticket",
            description="Testing ticket reopen",
            category_id=sample_category.id,
        ),
        current_user=customer_user,
    )
    await service.change_status(
        ticket.id,
        TicketStatusUpdate(status=TicketStatus.IN_PROGRESS),
        current_user=agent_user,
    )
    resolved = await service.change_status(
        ticket.id,
        TicketStatusUpdate(status=TicketStatus.RESOLVED),
        current_user=agent_user,
    )
    assert resolved.resolved_at is not None

    reopened = await service.change_status(
        ticket.id,
        TicketStatusUpdate(status=TicketStatus.IN_PROGRESS),
        current_user=agent_user,
    )
    assert reopened.status == TicketStatus.IN_PROGRESS
    assert reopened.resolved_at is None

    # 3. Agent cannot assign to other agent -> 403
    other_agent = await user_factory(
        email="other_agent_unit@test.com", role=UserRole.AGENT
    )
    with pytest.raises(HTTPException) as exc_ag_oth:
        await service.assign_ticket(
            ticket.id,
            TicketAssign(agent_id=other_agent.id),
            current_user=agent_user,
        )
    assert exc_ag_oth.value.status_code == 403

    # 4. Admin assigns to agent with data.agent_id
    assigned = await service.assign_ticket(
        ticket.id,
        TicketAssign(agent_id=other_agent.id),
        current_user=admin_user,
    )
    assert assigned.agent_id == other_agent.id

    # 5. Assign to target agent not found -> 404
    with pytest.raises(HTTPException) as exc_ag_nf:
        await service.assign_ticket(
            ticket.id,
            TicketAssign(agent_id=88888),
            current_user=admin_user,
        )
    assert exc_ag_nf.value.status_code == 404

    # 6. Assign to inactive agent -> 400
    inactive = await user_factory(
        email="inact_unit@test.com", role=UserRole.AGENT, is_active=False
    )
    with pytest.raises(HTTPException) as exc_ag_inact:
        await service.assign_ticket(
            ticket.id,
            TicketAssign(agent_id=inactive.id),
            current_user=admin_user,
        )
    assert exc_ag_inact.value.status_code == 400

    # 7. Assign to customer -> 400
    with pytest.raises(HTTPException) as exc_ag_cust:
        await service.assign_ticket(
            ticket.id,
            TicketAssign(agent_id=customer_user.id),
            current_user=admin_user,
        )
    assert exc_ag_cust.value.status_code == 400

    # 8. Invalid status transition -> 400
    fresh_ticket = await service.create_ticket(
        TicketCreate(
            title="Fresh Ticket",
            description="Testing invalid status transition",
            category_id=sample_category.id,
        ),
        current_user=customer_user,
    )
    with pytest.raises(HTTPException) as exc_inv_tr:
        await service.change_status(
            fresh_ticket.id,
            TicketStatusUpdate(status=TicketStatus.CLOSED),
            current_user=agent_user,
        )
    assert exc_inv_tr.value.status_code == 400


# --- User Service Privilege Escalation Test ---


@pytest.mark.asyncio
async def test_user_service_customer_cannot_change_role_or_active(
    db_session: AsyncSession, customer_user
):
    repo = UserRepository(db_session)
    service = UserService(repo)

    with pytest.raises(HTTPException) as exc_role:
        await service.update_user(
            user_id=customer_user.id,
            data=UserUpdate(role=UserRole.ADMIN),
            current_user=customer_user,
        )
    assert exc_role.value.status_code == 403


@pytest.mark.asyncio
async def test_ticket_service_crud_and_rbac(
    db_session: AsyncSession,
    customer_user,
    agent_user,
    admin_user,
    user_factory,
    sample_category,
):
    ticket_repo = TicketRepository(db_session)
    category_repo = CategoryRepository(db_session)
    user_repo = UserRepository(db_session)
    service = TicketService(ticket_repo, category_repo, user_repo)

    # 1. Create ticket - invalid category -> 404
    with pytest.raises(HTTPException) as exc_cat:
        await service.create_ticket(
            TicketCreate(
                title="Bad Cat",
                description="Valid description here",
                category_id=99999,
            ),
            current_user=customer_user,
        )
    assert exc_cat.value.status_code == 404

    # 2. Create ticket - success
    ticket = await service.create_ticket(
        TicketCreate(
            title="Service Ticket",
            description="Testing service create ticket",
            category_id=sample_category.id,
        ),
        current_user=customer_user,
    )
    assert ticket.id is not None
    assert ticket.status == TicketStatus.OPEN

    # 3. Get ticket - forbidden for another customer
    other_customer = await user_factory(email="other_cust@test.com")
    with pytest.raises(HTTPException) as exc_forbid:
        await service.get_ticket(ticket.id, current_user=other_customer)
    assert exc_forbid.value.status_code == 403

    # 4. Get ticket - success for owner customer and staff
    fetched = await service.get_ticket(ticket.id, current_user=customer_user)
    assert fetched.id == ticket.id
    fetched_admin = await service.get_ticket(ticket.id, current_user=admin_user)
    assert fetched_admin.id == ticket.id

    # 5. List tickets
    page_resp = await service.list_tickets(current_user=customer_user, page=1, limit=10)
    assert page_resp.total >= 1

    # 6. Change Priority - customer forbidden
    with pytest.raises(HTTPException) as exc_prio_cust:
        await service.change_priority(
            ticket.id,
            TicketPriorityUpdate(priority=TicketPriority.URGENT),
            current_user=customer_user,
        )
    assert exc_prio_cust.value.status_code == 403

    # 7. Change Priority - success by agent
    updated_prio = await service.change_priority(
        ticket.id,
        TicketPriorityUpdate(priority=TicketPriority.URGENT),
        current_user=agent_user,
    )
    assert updated_prio.priority == TicketPriority.URGENT

    # Same priority -> 400
    with pytest.raises(HTTPException) as exc_same_prio:
        await service.change_priority(
            ticket.id,
            TicketPriorityUpdate(priority=TicketPriority.URGENT),
            current_user=agent_user,
        )
    assert exc_same_prio.value.status_code == 400

    # 8. Assign ticket - customer forbidden
    with pytest.raises(HTTPException) as exc_assign_cust:
        await service.assign_ticket(
            ticket.id,
            TicketAssign(agent_id=agent_user.id),
            current_user=customer_user,
        )
    assert exc_assign_cust.value.status_code == 403

    # Assign ticket - agent assigns to self -> success
    assigned = await service.assign_ticket(
        ticket.id,
        TicketAssign(agent_id=agent_user.id),
        current_user=agent_user,
    )
    assert assigned.agent_id == agent_user.id
    assert assigned.status == TicketStatus.IN_PROGRESS

    # 9. Change status - customer forbidden
    with pytest.raises(HTTPException) as exc_st_cust:
        await service.change_status(
            ticket.id,
            TicketStatusUpdate(status=TicketStatus.RESOLVED),
            current_user=customer_user,
        )
    assert exc_st_cust.value.status_code == 403

    # Change status - same status -> 400
    with pytest.raises(HTTPException) as exc_st_same:
        await service.change_status(
            ticket.id,
            TicketStatusUpdate(status=TicketStatus.IN_PROGRESS),
            current_user=agent_user,
        )
    assert exc_st_same.value.status_code == 400

    # Change status - IN_PROGRESS -> RESOLVED -> CLOSED
    res = await service.change_status(
        ticket.id,
        TicketStatusUpdate(status=TicketStatus.RESOLVED),
        current_user=agent_user,
    )
    assert res.status == TicketStatus.RESOLVED
    assert res.resolved_at is not None

    closed = await service.change_status(
        ticket.id,
        TicketStatusUpdate(status=TicketStatus.CLOSED),
        current_user=agent_user,
    )
    assert closed.status == TicketStatus.CLOSED
    assert closed.closed_at is not None

    # On closed ticket, assign and change priority fail with 400
    with pytest.raises(HTTPException) as exc_cl_assign:
        await service.assign_ticket(
            ticket.id,
            TicketAssign(agent_id=agent_user.id),
            current_user=admin_user,
        )
    assert exc_cl_assign.value.status_code == 400

    with pytest.raises(HTTPException) as exc_cl_prio:
        await service.change_priority(
            ticket.id,
            TicketPriorityUpdate(priority=TicketPriority.LOW),
            current_user=agent_user,
        )
    assert exc_cl_prio.value.status_code == 400


# --- State Machine & Security Tests ---


def test_ticket_state_machine_transition_invalid():
    with pytest.raises(ValueError) as exc:
        TicketStateMachine.transition(TicketStatus.OPEN, TicketStatus.CLOSED)
    assert "Invalid transition" in str(exc.value)

    res = TicketStateMachine.transition(TicketStatus.OPEN, TicketStatus.IN_PROGRESS)
    assert res == TicketStatus.IN_PROGRESS


def test_security_create_refresh_token_custom_delta():
    custom_delta = timedelta(days=2)
    token = create_refresh_token(subject=1, expires_delta=custom_delta)
    assert token is not None
