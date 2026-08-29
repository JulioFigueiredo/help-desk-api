import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.user import User


@pytest.mark.asyncio
async def test_create_category_as_admin(
    client: AsyncClient, admin_user: User, auth_headers
):
    payload = {
        "name": "Billing Issues",
        "description": "Questions about invoices and charges",
    }
    response = await client.post(
        "/api/v1/categories/",
        json=payload,
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Billing Issues"
    assert data["description"] == "Questions about invoices and charges"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_category_forbidden_for_customer(
    client: AsyncClient, customer_user: User, auth_headers
):
    payload = {"name": "Unauthorized Category"}
    response = await client.post(
        "/api/v1/categories/",
        json=payload,
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_create_category_forbidden_for_agent(
    client: AsyncClient, agent_user: User, auth_headers
):
    payload = {"name": "Agent Category"}
    response = await client.post(
        "/api/v1/categories/",
        json=payload,
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_create_category_unauthenticated(client: AsyncClient):
    response = await client.post(
        "/api/v1/categories/",
        json={"name": "No Auth"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_category_duplicate_name(
    client: AsyncClient, admin_user: User, sample_category: Category, auth_headers
):
    payload = {"name": sample_category.name, "description": "Duplicate category"}
    response = await client.post(
        "/api/v1/categories/",
        json=payload,
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Category already exists"


@pytest.mark.asyncio
async def test_list_categories_authenticated(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    response = await client.get(
        "/api/v1/categories/",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert any(cat["name"] == sample_category.name for cat in data)


@pytest.mark.asyncio
async def test_list_categories_unauthenticated(client: AsyncClient):
    response = await client.get("/api/v1/categories/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_category_by_id_success(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    response = await client.get(
        f"/api/v1/categories/{sample_category.id}",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_category.id
    assert data["name"] == sample_category.name


@pytest.mark.asyncio
async def test_get_category_not_found(
    client: AsyncClient, customer_user: User, auth_headers
):
    response = await client.get(
        "/api/v1/categories/99999",
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"
