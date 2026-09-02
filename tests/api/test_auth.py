from datetime import UTC, datetime, timedelta

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User, UserRole


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    payload = {
        "name": "Jane Doe",
        "email": "janedoe@example.com",
        "password": "strongpassword123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "janedoe@example.com"
    assert data["role"] == "CUSTOMER"
    assert data["is_active"] is True
    assert "id" in data
    assert "hashed_password" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, customer_user: User):
    payload = {
        "name": "Duplicate User",
        "email": customer_user.email,
        "password": "strongpassword123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already registered"


@pytest.mark.asyncio
async def test_register_invalid_payload(client: AsyncClient):
    # Short password
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test", "email": "valid@example.com", "password": "123"},
    )
    assert response.status_code == 422

    # Invalid email
    response = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test", "email": "not-an-email", "password": "password123"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_ignores_requested_role(client: AsyncClient):
    payload = {
        "name": "Hacker",
        "email": "hacker@example.com",
        "password": "strongpassword123",
        "role": "ADMIN",
    }
    response = await client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["role"] == "CUSTOMER"


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, user_factory):
    await user_factory(
        email="login_user@example.com",
        password="correctpassword123",
        role=UserRole.CUSTOMER,
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_user@example.com", "password": "correctpassword123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, user_factory):
    await user_factory(
        email="login_user@example.com",
        password="correctpassword123",
    )

    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_user@example.com", "password": "wrongpassword123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "password123"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


@pytest.mark.asyncio
async def test_login_inactive_user(client: AsyncClient, inactive_user: User):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": inactive_user.email, "password": "securepassword123"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user account"


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, customer_user: User):
    refresh_token = create_refresh_token(subject=customer_user.id)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


@pytest.mark.asyncio
async def test_refresh_token_access_token_provided(
    client: AsyncClient, customer_user: User
):
    # Providing an access token instead of a refresh token should fail
    access_token = create_access_token(
        subject=customer_user.id, role=customer_user.role
    )

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


@pytest.mark.asyncio
async def test_refresh_token_expired(client: AsyncClient):
    expired_time = datetime.now(UTC) - timedelta(days=1)
    expired_token = jwt.encode(
        {"sub": "1", "exp": expired_time, "type": "refresh"},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": expired_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired refresh token"


@pytest.mark.asyncio
async def test_refresh_token_inactive_user(client: AsyncClient, inactive_user: User):
    refresh_token = create_refresh_token(subject=inactive_user.id)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user account"


@pytest.mark.asyncio
async def test_refresh_token_user_not_found(client: AsyncClient):
    # Non-existent user id in token
    refresh_token = create_refresh_token(subject=99999)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "User not found"
