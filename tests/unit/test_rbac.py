import pytest
from fastapi import HTTPException

from app.api.v1.dependencies import (
    RoleChecker,
    require_admin,
    require_agent,
    require_customer,
    require_staff,
)
from app.models.user import User, UserRole


def create_mock_user(role: UserRole, is_active: bool = True) -> User:
    return User(
        id=1,
        name="Test User",
        email="test@example.com",
        hashed_password="hashed_password",
        role=role,
        is_active=is_active,
    )


@pytest.mark.asyncio
async def test_role_checker_allows_valid_role():
    checker = RoleChecker([UserRole.ADMIN, UserRole.AGENT])
    user = create_mock_user(UserRole.ADMIN)

    result = await checker(current_user=user)
    assert result == user


@pytest.mark.asyncio
async def test_role_checker_blocks_invalid_role():
    checker = RoleChecker([UserRole.ADMIN])
    user = create_mock_user(UserRole.CUSTOMER)

    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_require_admin():
    admin = create_mock_user(UserRole.ADMIN)
    agent = create_mock_user(UserRole.AGENT)
    customer = create_mock_user(UserRole.CUSTOMER)

    assert await require_admin(current_user=admin) == admin

    with pytest.raises(HTTPException) as exc_agent:
        await require_admin(current_user=agent)
    assert exc_agent.value.status_code == 403

    with pytest.raises(HTTPException) as exc_customer:
        await require_admin(current_user=customer)
    assert exc_customer.value.status_code == 403


@pytest.mark.asyncio
async def test_require_staff():
    admin = create_mock_user(UserRole.ADMIN)
    agent = create_mock_user(UserRole.AGENT)
    customer = create_mock_user(UserRole.CUSTOMER)

    assert await require_staff(current_user=admin) == admin
    assert await require_staff(current_user=agent) == agent

    with pytest.raises(HTTPException) as exc:
        await require_staff(current_user=customer)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_agent():
    agent = create_mock_user(UserRole.AGENT)
    admin = create_mock_user(UserRole.ADMIN)

    assert await require_agent(current_user=agent) == agent

    with pytest.raises(HTTPException) as exc:
        await require_agent(current_user=admin)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_customer():
    customer = create_mock_user(UserRole.CUSTOMER)
    agent = create_mock_user(UserRole.AGENT)

    assert await require_customer(current_user=customer) == customer

    with pytest.raises(HTTPException) as exc:
        await require_customer(current_user=agent)
    assert exc.value.status_code == 403
