import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.user import User


@pytest.mark.asyncio
async def test_create_ticket_success(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    payload = {
        "title": "Cannot access billing dashboard",
        "description": "Whenever I click billing, it throws a 500 error on screen.",
        "category_id": sample_category.id,
        "priority": "HIGH",
    }
    response = await client.post(
        "/api/v1/tickets/",
        json=payload,
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["status"] == "OPEN"
    assert data["priority"] == "HIGH"
    assert data["customer_id"] == customer_user.id
    assert data["agent_id"] is None
    assert data["category_id"] == sample_category.id
    assert "id" in data


@pytest.mark.asyncio
async def test_create_ticket_unauthenticated(
    client: AsyncClient, sample_category: Category
):
    payload = {
        "title": "Unauthenticated ticket",
        "description": "This should fail because no JWT token is provided.",
        "category_id": sample_category.id,
    }
    response = await client.post("/api/v1/tickets/", json=payload)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_ticket_nonexistent_category(
    client: AsyncClient, customer_user: User, auth_headers
):
    payload = {
        "title": "Ticket with bad category",
        "description": "Category ID does not exist in database.",
        "category_id": 99999,
    }
    response = await client.post(
        "/api/v1/tickets/",
        json=payload,
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Category not found"


@pytest.mark.asyncio
async def test_create_ticket_validation_error(
    client: AsyncClient, customer_user: User, sample_category: Category, auth_headers
):
    # Description shorter than 10 characters should trigger 422
    payload = {
        "title": "Short desc",
        "description": "short",
        "category_id": sample_category.id,
    }
    response = await client.post(
        "/api/v1/tickets/",
        json=payload,
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_ticket_own_success(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    # 1. Create a ticket
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "My personal ticket",
            "description": "Checking if detailed response has nested relationships.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # 2. Get ticket by ID
    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket_id
    assert data["customer"]["id"] == customer_user.id
    assert data["customer"]["email"] == customer_user.email
    assert data["category"]["id"] == sample_category.id
    assert data["category"]["name"] == sample_category.name
    assert data["agent"] is None


@pytest.mark.asyncio
async def test_get_ticket_forbidden_for_other_customer(
    client: AsyncClient,
    customer_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    # Customer 1 creates a ticket
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer 1 private ticket",
            "description": "Sensitive customer data that should be private.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Customer 2 tries to access Customer 1's ticket
    other_customer = await user_factory(
        email="other_customer@example.com", name="Other Customer"
    )
    response = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_headers(other_customer),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_get_ticket_admin_and_agent_can_access_any(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    # Customer creates a ticket
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer issue for staff",
            "description": "Staff members should be able to view this ticket.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Agent accesses ticket
    agent_resp = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_headers(agent_user),
    )
    assert agent_resp.status_code == 200

    # Admin accesses ticket
    admin_resp = await client.get(
        f"/api/v1/tickets/{ticket_id}",
        headers=auth_headers(admin_user),
    )
    assert admin_resp.status_code == 200


@pytest.mark.asyncio
async def test_get_ticket_not_found(
    client: AsyncClient, customer_user: User, auth_headers
):
    response = await client.get(
        "/api/v1/tickets/99999",
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


@pytest.mark.asyncio
async def test_list_tickets_customer_tenant_isolation(
    client: AsyncClient,
    customer_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    # Customer 1 creates a ticket
    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer 1 Ticket",
            "description": "Belongs exclusively to customer 1.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )

    # Customer 2 creates a ticket
    other_customer = await user_factory(
        email="second_customer@example.com", name="Second Customer"
    )
    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer 2 Ticket",
            "description": "Belongs exclusively to customer 2.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(other_customer),
    )

    # When Customer 1 lists tickets, only 1 ticket should be returned
    response = await client.get(
        "/api/v1/tickets/",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["customer_id"] == customer_user.id


@pytest.mark.asyncio
async def test_list_tickets_admin_sees_all(
    client: AsyncClient,
    customer_user: User,
    admin_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    # Create tickets for two different customers
    other_customer = await user_factory(
        email="third_customer@example.com", name="Third Customer"
    )
    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer A Ticket",
            "description": "Description for customer A ticket.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer B Ticket",
            "description": "Description for customer B ticket.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(other_customer),
    )

    # Admin lists tickets
    response = await client.get(
        "/api/v1/tickets/",
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


@pytest.mark.asyncio
async def test_list_tickets_filters_priority_and_category(
    client: AsyncClient,
    admin_user: User,
    category_factory,
    auth_headers,
):
    cat_alpha = await category_factory(name="Alpha Support")
    cat_beta = await category_factory(name="Beta Support")

    # Ticket 1: LOW, cat_alpha
    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Low priority Alpha",
            "description": "Low priority ticket in Alpha category.",
            "category_id": cat_alpha.id,
            "priority": "LOW",
        },
        headers=auth_headers(admin_user),
    )

    # Ticket 2: URGENT, cat_beta
    await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Urgent priority Beta",
            "description": "Urgent priority ticket in Beta category.",
            "category_id": cat_beta.id,
            "priority": "URGENT",
        },
        headers=auth_headers(admin_user),
    )

    # Filter by priority=URGENT
    prio_resp = await client.get(
        "/api/v1/tickets/?priority=URGENT",
        headers=auth_headers(admin_user),
    )
    assert prio_resp.status_code == 200
    prio_data = prio_resp.json()
    assert prio_data["total"] == 1
    assert prio_data["items"][0]["priority"] == "URGENT"

    # Filter by category_id=cat_alpha.id
    cat_resp = await client.get(
        f"/api/v1/tickets/?category_id={cat_alpha.id}",
        headers=auth_headers(admin_user),
    )
    assert cat_resp.status_code == 200
    cat_data = cat_resp.json()
    assert cat_data["total"] == 1
    assert cat_data["items"][0]["category_id"] == cat_alpha.id


@pytest.mark.asyncio
async def test_list_tickets_pagination(
    client: AsyncClient,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    # Create 3 tickets
    for i in range(3):
        await client.post(
            "/api/v1/tickets/",
            json={
                "title": f"Paginated Ticket {i}",
                "description": f"Detailed description for paginated ticket {i}",
                "category_id": sample_category.id,
            },
            headers=auth_headers(admin_user),
        )

    # Request page 1 with limit 2
    page1_resp = await client.get(
        "/api/v1/tickets/?page=1&limit=2",
        headers=auth_headers(admin_user),
    )
    assert page1_resp.status_code == 200
    page1 = page1_resp.json()
    assert page1["total"] == 3
    assert page1["page"] == 1
    assert page1["limit"] == 2
    assert page1["total_pages"] == 2
    assert len(page1["items"]) == 2

    # Request page 2 with limit 2
    page2_resp = await client.get(
        "/api/v1/tickets/?page=2&limit=2",
        headers=auth_headers(admin_user),
    )
    assert page2_resp.status_code == 200
    page2 = page2_resp.json()
    assert page2["total"] == 3
    assert page2["page"] == 2
    assert page2["total_pages"] == 2
    assert len(page2["items"]) == 1
