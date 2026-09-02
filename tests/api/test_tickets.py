import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.user import User, UserRole


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


# --- Assign Ticket Tests ---


@pytest.mark.asyncio
async def test_assign_ticket_agent_to_self_success(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    # Customer creates a ticket
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Need help with login",
            "description": "I cannot login to my customer dashboard.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Agent assigns ticket to self (empty payload)
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket_id
    assert data["agent_id"] == agent_user.id
    assert data["status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_assign_ticket_admin_to_agent_success(
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
            "title": "Database connection drop",
            "description": "Database connection is dropping intermittently.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Admin assigns ticket to agent
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"agent_id": agent_user.id},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket_id
    assert data["agent_id"] == agent_user.id
    assert data["status"] == "IN_PROGRESS"


@pytest.mark.asyncio
async def test_assign_ticket_customer_forbidden(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer trying to assign",
            "description": "Customer should never be allowed to assign tickets.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"agent_id": agent_user.id},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_assign_ticket_agent_cannot_assign_to_other_agent(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    other_agent = await user_factory(
        email="other_agent@example.com",
        name="Other Agent",
        role=UserRole.AGENT,
    )

    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Ticket assignment delegation",
            "description": "Agent cannot reassign to another agent.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Agent tries to assign to other_agent
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"agent_id": other_agent.id},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Agents can only attribute tickets for yourself"


@pytest.mark.asyncio
async def test_assign_ticket_target_agent_not_found(
    client: AsyncClient,
    customer_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Ghost agent ticket",
            "description": "Assigning to a nonexistent agent ID.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"agent_id": 99999},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Agent not found"


@pytest.mark.asyncio
async def test_assign_ticket_target_cannot_be_customer(
    client: AsyncClient,
    customer_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer as agent ticket",
            "description": "Assigning ticket to a customer is forbidden.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"agent_id": customer_user.id},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Target user must be an agent or admin"


@pytest.mark.asyncio
async def test_assign_ticket_target_inactive_user(
    client: AsyncClient,
    customer_user: User,
    admin_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    inactive_agent = await user_factory(
        email="inactive_agent@example.com",
        name="Inactive Agent",
        role=UserRole.AGENT,
        is_active=False,
    )

    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Inactive agent ticket",
            "description": "Assigning ticket to an inactive agent.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/assign",
        json={"agent_id": inactive_agent.id},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot assign ticket to an inactive user"


@pytest.mark.asyncio
async def test_assign_ticket_not_found(
    client: AsyncClient,
    admin_user: User,
    auth_headers,
):
    response = await client.post(
        "/api/v1/tickets/99999/assign",
        json={},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


# --- Change Ticket Status Tests ---


@pytest.mark.asyncio
async def test_change_status_full_lifecycle_and_timestamps(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    # 1. Customer creates a ticket (starts in OPEN)
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "System slow after release",
            "description": "The system response time increased noticeably.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # 2. Agent transitions OPEN -> IN_PROGRESS
    resp1 = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(agent_user),
    )
    assert resp1.status_code == 200
    assert resp1.json()["status"] == "IN_PROGRESS"
    assert resp1.json()["resolved_at"] is None
    assert resp1.json()["closed_at"] is None

    # 3. Agent transitions IN_PROGRESS -> RESOLVED (sets resolved_at)
    resp2 = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "RESOLVED"},
        headers=auth_headers(agent_user),
    )
    assert resp2.status_code == 200
    assert resp2.json()["status"] == "RESOLVED"
    assert resp2.json()["resolved_at"] is not None
    assert resp2.json()["closed_at"] is None

    # 4. Agent reopens ticket RESOLVED -> IN_PROGRESS (clears resolved_at)
    resp3 = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(agent_user),
    )
    assert resp3.status_code == 200
    assert resp3.json()["status"] == "IN_PROGRESS"
    assert resp3.json()["resolved_at"] is None

    # 5. Agent resolves again IN_PROGRESS -> RESOLVED
    resp4 = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "RESOLVED"},
        headers=auth_headers(agent_user),
    )
    assert resp4.status_code == 200
    assert resp4.json()["status"] == "RESOLVED"
    assert resp4.json()["resolved_at"] is not None

    # 6. Admin closes ticket RESOLVED -> CLOSED (sets closed_at)
    resp5 = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "CLOSED"},
        headers=auth_headers(admin_user),
    )
    assert resp5.status_code == 200
    assert resp5.json()["status"] == "CLOSED"
    assert resp5.json()["closed_at"] is not None


@pytest.mark.asyncio
async def test_change_status_invalid_transition_from_open_to_closed(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Direct close attempt",
            "description": "Tickets cannot jump straight from OPEN to CLOSED.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "CLOSED"},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 400
    assert "Invalid transition from OPEN to CLOSED" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_status_closed_ticket_is_terminal(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    # Create ticket
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Terminal ticket test",
            "description": "Closed tickets cannot transition to any other status.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Progress to CLOSED
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(agent_user),
    )
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "RESOLVED"},
        headers=auth_headers(agent_user),
    )
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "CLOSED"},
        headers=auth_headers(agent_user),
    )

    # Attempt to reopen from CLOSED to IN_PROGRESS
    reopen_resp = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(agent_user),
    )
    assert reopen_resp.status_code == 400
    assert (
        "Invalid transition from CLOSED to IN_PROGRESS" in reopen_resp.json()["detail"]
    )


@pytest.mark.asyncio
async def test_change_status_same_status_bad_request(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Same status test",
            "description": "Changing status to identical status should fail.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "OPEN"},
        headers=auth_headers(agent_user),
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Ticket is already in this status"


@pytest.mark.asyncio
async def test_change_status_customer_forbidden(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer status test",
            "description": "Customer cannot change status of any ticket.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_change_status_not_found(
    client: AsyncClient,
    agent_user: User,
    auth_headers,
):
    response = await client.patch(
        "/api/v1/tickets/99999/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(agent_user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


@pytest.mark.asyncio
async def test_change_priority_agent_success(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Database connection slow",
            "description": "Queries are taking more than 10 seconds to execute.",
            "category_id": sample_category.id,
            "priority": "MEDIUM",
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "HIGH"},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == ticket_id
    assert data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_change_priority_admin_success(
    client: AsyncClient,
    customer_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Payment gateway downtime",
            "description": "All checkout requests are failing immediately.",
            "category_id": sample_category.id,
            "priority": "LOW",
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "URGENT"},
        headers=auth_headers(admin_user),
    )

    assert response.status_code == 200
    assert response.json()["priority"] == "URGENT"


@pytest.mark.asyncio
async def test_change_priority_customer_forbidden(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Customer attempts priority escalation",
            "description": "Customers should not be allowed to change ticket priority.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "URGENT"},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_change_priority_not_found(
    client: AsyncClient,
    agent_user: User,
    auth_headers,
):
    response = await client.patch(
        "/api/v1/tickets/99999/priority",
        json={"priority": "HIGH"},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


@pytest.mark.asyncio
async def test_change_priority_same_priority_bad_request(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Priority same value check",
            "description": "Changing to identical priority should return bad request.",
            "category_id": sample_category.id,
            "priority": "MEDIUM",
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "MEDIUM"},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Ticket is already in this priority"


@pytest.mark.asyncio
async def test_change_priority_closed_ticket_bad_request(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Closed ticket priority change attempt",
            "description": "Closed tickets cannot have their priority updated.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    # Transition to CLOSED: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "IN_PROGRESS"},
        headers=auth_headers(agent_user),
    )
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "RESOLVED"},
        headers=auth_headers(agent_user),
    )
    await client.patch(
        f"/api/v1/tickets/{ticket_id}/status",
        json={"status": "CLOSED"},
        headers=auth_headers(agent_user),
    )

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "HIGH"},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Ticket is closed"


@pytest.mark.asyncio
async def test_change_priority_invalid_value_validation_error(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    create_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Invalid priority enum test",
            "description": "Invalid enum value should fail Pydantic validation.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = create_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/tickets/{ticket_id}/priority",
        json={"priority": "SUPER_URGENT"},
        headers=auth_headers(agent_user),
    )

    assert response.status_code == 422
