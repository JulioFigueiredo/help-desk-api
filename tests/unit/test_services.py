import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, RefreshTokenRequest
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import AuthService
from app.services.user_service import UserService


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


@pytest.mark.asyncio
async def test_message_service_ticket_not_found(
    db_session: AsyncSession, customer_user
):
    from app.repositories.message_repo import MessageRepository
    from app.repositories.ticket_repo import TicketRepository
    from app.schemas.message import MessageCreate
    from app.services.message_service import MessageService

    service = MessageService(
        message_repo=MessageRepository(db_session),
        ticket_repo=TicketRepository(db_session),
    )

    with pytest.raises(HTTPException) as exc:
        await service.create_message(
            ticket_id=99999,
            data=MessageCreate(content="Testing ticket not found"),
            current_user=customer_user,
        )
    assert exc.value.status_code == 404

    with pytest.raises(HTTPException) as exc:
        await service.list_messages(ticket_id=99999, current_user=customer_user)
    assert exc.value.status_code == 404
