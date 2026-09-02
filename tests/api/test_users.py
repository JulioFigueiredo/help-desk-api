import pytest
from httpx import AsyncClient

from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient, customer_user: User, auth_headers):
    response = await client.get("/api/v1/users/me", headers=auth_headers(customer_user))

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == customer_user.id
    assert data["email"] == customer_user.email
    assert data["role"] == "CUSTOMER"
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_inactive_user(
    client: AsyncClient, inactive_user: User, auth_headers
):
    response = await client.get("/api/v1/users/me", headers=auth_headers(inactive_user))
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_list_users_as_admin(
    client: AsyncClient,
    admin_user: User,
    customer_user: User,
    agent_user: User,
    auth_headers,
):
    response = await client.get("/api/v1/users/", headers=auth_headers(admin_user))

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3


@pytest.mark.asyncio
async def test_list_users_forbidden_for_customer(
    client: AsyncClient, customer_user: User, auth_headers
):
    response = await client.get("/api/v1/users/", headers=auth_headers(customer_user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_users_forbidden_for_agent(
    client: AsyncClient, agent_user: User, auth_headers
):
    response = await client.get("/api/v1/users/", headers=auth_headers(agent_user))
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_create_user_as_admin(
    client: AsyncClient, admin_user: User, auth_headers
):
    payload = {
        "name": "New Agent",
        "email": "newagent@example.com",
        "password": "password123",
        "role": "AGENT",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newagent@example.com"
    assert data["name"] == "New Agent"


@pytest.mark.asyncio
async def test_create_user_forbidden_for_customer(
    client: AsyncClient, customer_user: User, auth_headers
):
    payload = {
        "name": "New Person",
        "email": "person@example.com",
        "password": "password123",
    }
    response = await client.post(
        "/api/v1/users/",
        json=payload,
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_user_own_profile(
    client: AsyncClient, customer_user: User, auth_headers
):
    response = await client.get(
        f"/api/v1/users/{customer_user.id}",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    assert response.json()["id"] == customer_user.id


@pytest.mark.asyncio
async def test_get_user_admin_can_access_others(
    client: AsyncClient, admin_user: User, customer_user: User, auth_headers
):
    response = await client.get(
        f"/api/v1/users/{customer_user.id}",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    assert response.json()["id"] == customer_user.id


@pytest.mark.asyncio
async def test_get_user_customer_cannot_access_others(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/users/{agent_user.id}",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_get_user_not_found(client: AsyncClient, admin_user: User, auth_headers):
    response = await client.get(
        "/api/v1/users/99999",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


@pytest.mark.asyncio
async def test_update_user_own_name(
    client: AsyncClient, customer_user: User, auth_headers
):
    response = await client.patch(
        f"/api/v1/users/{customer_user.id}",
        json={"name": "Updated Customer Name"},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Customer Name"


@pytest.mark.asyncio
async def test_update_user_customer_cannot_change_role_or_status(
    client: AsyncClient, customer_user: User, auth_headers
):
    # Attempting to escalate to ADMIN
    response = await client.patch(
        f"/api/v1/users/{customer_user.id}",
        json={"role": "ADMIN"},
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot change role or status"

    # Attempting to change is_active
    response = await client.patch(
        f"/api/v1/users/{customer_user.id}",
        json={"is_active": False},
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Cannot change role or status"


@pytest.mark.asyncio
async def test_update_user_admin_can_change_role_and_status(
    client: AsyncClient, admin_user: User, customer_user: User, auth_headers
):
    response = await client.patch(
        f"/api/v1/users/{customer_user.id}",
        json={"role": "AGENT", "is_active": False},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "AGENT"
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_update_user_duplicate_email(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    auth_headers,
):
    response = await client.patch(
        f"/api/v1/users/{customer_user.id}",
        json={"email": agent_user.email},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_update_user_forbidden_for_other_customer(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    auth_headers,
):
    response = await client.patch(
        f"/api/v1/users/{agent_user.id}",
        json={"name": "Tampered Name"},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_type(client: AsyncClient):
    # Pass refresh token to an endpoint requiring access token
    from app.core.security import create_refresh_token

    refresh_token = create_refresh_token(subject=1)
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refresh_token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_non_integer_sub(client: AsyncClient):
    import jwt

    from app.core.config import settings

    token = jwt.encode(
        {"sub": "not-a-number", "type": "access", "role": "CUSTOMER"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_deleted_from_db(client: AsyncClient):
    from app.core.security import create_access_token

    token = create_access_token(subject=99999, role=UserRole.CUSTOMER)
    response = await client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_users_pagination(
    client: AsyncClient,
    admin_user: User,
    customer_user: User,
    agent_user: User,
    auth_headers,
):
    response = await client.get(
        "/api/v1/users/?skip=1&limit=1",
        headers=auth_headers(admin_user),
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
