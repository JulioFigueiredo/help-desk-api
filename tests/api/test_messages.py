import pytest
from httpx import AsyncClient

from app.models.category import Category
from app.models.user import User


@pytest.mark.asyncio
async def test_create_message_customer_success(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    # 1. Create a ticket
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Cannot download invoices",
            "description": "Invoice download button fails with network error.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # 2. Customer creates a message on the ticket
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Here is additional context: it happens on Chrome browser."},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ticket_id"] == ticket_id
    assert data["author_id"] == customer_user.id
    assert (
        data["content"] == "Here is additional context: it happens on Chrome browser."
    )
    assert data["author"]["id"] == customer_user.id
    assert data["author"]["email"] == customer_user.email
    assert data["author"]["role"] == "CUSTOMER"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_create_message_agent_and_admin_success(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    # Customer creates a ticket
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Server response high latency",
            "description": "API responses take more than 5 seconds.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # Agent responds on ticket
    agent_resp = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Hello! I am investigating the logs right now."},
        headers=auth_headers(agent_user),
    )
    assert agent_resp.status_code == 201
    agent_data = agent_resp.json()
    assert agent_data["ticket_id"] == ticket_id
    assert agent_data["author_id"] == agent_user.id
    assert agent_data["author"]["role"] == "AGENT"

    # Admin responds on ticket
    admin_resp = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Admin override note: escalated to infrastructure team."},
        headers=auth_headers(admin_user),
    )
    assert admin_resp.status_code == 201
    admin_data = admin_resp.json()
    assert admin_data["ticket_id"] == ticket_id
    assert admin_data["author_id"] == admin_user.id
    assert admin_data["author"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_create_message_forbidden_for_other_customer(
    client: AsyncClient,
    customer_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    # Customer 1 creates ticket
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Confidential customer issue",
            "description": "Sensitive billing details of customer 1.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # Customer 2 attempts to post message on Customer 1's ticket
    other_customer = await user_factory(
        email="stranger@example.com", name="Stranger Customer"
    )
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Trying to inject message into someone else's ticket."},
        headers=auth_headers(other_customer),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_create_message_ticket_closed_bad_request(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    # 1. Customer creates ticket
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Bug resolved ticket",
            "description": "Bug was fixed, ticket will be closed.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # 2. Advance status: OPEN -> IN_PROGRESS -> RESOLVED -> CLOSED
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

    # 3. Attempt to post message on CLOSED ticket
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Trying to send message on closed ticket."},
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Ticket is closed"

    # Agent also cannot post on CLOSED ticket
    agent_msg_resp = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Agent trying to send message on closed ticket."},
        headers=auth_headers(agent_user),
    )
    assert agent_msg_resp.status_code == 400
    assert agent_msg_resp.json()["detail"] == "Ticket is closed"


@pytest.mark.asyncio
async def test_create_message_ticket_not_found(
    client: AsyncClient,
    customer_user: User,
    auth_headers,
):
    response = await client.post(
        "/api/v1/tickets/99999/messages",
        json={"content": "Message for nonexistent ticket."},
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


@pytest.mark.asyncio
async def test_create_message_unauthenticated(
    client: AsyncClient,
    sample_category: Category,
    customer_user: User,
    auth_headers,
):
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Unauth ticket message test",
            "description": "Testing unauthenticated message posting.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Unauthenticated message payload."},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_message_inactive_user(
    client: AsyncClient,
    customer_user: User,
    inactive_user: User,
    sample_category: Category,
    auth_headers,
):
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Inactive user test",
            "description": "Testing inactive user message rejection.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Inactive user sending message."},
        headers=auth_headers(inactive_user),
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Inactive user"


@pytest.mark.asyncio
async def test_create_message_validation_error(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Validation error test",
            "description": "Testing schema validation for messages.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # Short content (< 2 chars)
    response = await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "a"},
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_messages_customer_own_ticket_and_ordering(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    # 1. Create ticket
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Conversation thread ticket",
            "description": "Conversation with multiple back-and-forth messages.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # 2. Before any messages, list should be empty
    empty_resp = await client.get(
        f"/api/v1/tickets/{ticket_id}/messages",
        headers=auth_headers(customer_user),
    )
    assert empty_resp.status_code == 200
    assert empty_resp.json() == []

    # 3. Create 3 messages
    await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "First message from customer"},
        headers=auth_headers(customer_user),
    )
    await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Second message from agent"},
        headers=auth_headers(agent_user),
    )
    await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Third message from customer follow-up"},
        headers=auth_headers(customer_user),
    )

    # 4. Customer lists messages
    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/messages",
        headers=auth_headers(customer_user),
    )

    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 3
    assert messages[0]["content"] == "First message from customer"
    assert messages[0]["author"]["id"] == customer_user.id
    assert messages[1]["content"] == "Second message from agent"
    assert messages[1]["author"]["id"] == agent_user.id
    assert messages[2]["content"] == "Third message from customer follow-up"
    assert messages[2]["author"]["id"] == customer_user.id


@pytest.mark.asyncio
async def test_list_messages_agent_and_admin_can_access_any(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    admin_user: User,
    sample_category: Category,
    auth_headers,
):
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Staff viewing messages",
            "description": "Staff should have access to list messages for all tickets.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Initial customer message."},
        headers=auth_headers(customer_user),
    )

    # Agent lists
    agent_resp = await client.get(
        f"/api/v1/tickets/{ticket_id}/messages",
        headers=auth_headers(agent_user),
    )
    assert agent_resp.status_code == 200
    assert len(agent_resp.json()) == 1

    # Admin lists
    admin_resp = await client.get(
        f"/api/v1/tickets/{ticket_id}/messages",
        headers=auth_headers(admin_user),
    )
    assert admin_resp.status_code == 200
    assert len(admin_resp.json()) == 1


@pytest.mark.asyncio
async def test_list_messages_forbidden_for_other_customer(
    client: AsyncClient,
    customer_user: User,
    user_factory,
    sample_category: Category,
    auth_headers,
):
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Private conversation",
            "description": "Private messages between customer 1 and support.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    other_customer = await user_factory(
        email="outsider@example.com", name="Outsider Customer"
    )

    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/messages",
        headers=auth_headers(other_customer),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "The user doesn't have enough privileges"


@pytest.mark.asyncio
async def test_list_messages_ticket_not_found(
    client: AsyncClient,
    customer_user: User,
    auth_headers,
):
    response = await client.get(
        "/api/v1/tickets/99999/messages",
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


@pytest.mark.asyncio
async def test_list_messages_unauthenticated(
    client: AsyncClient,
    customer_user: User,
    sample_category: Category,
    auth_headers,
):
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Unauth list messages test",
            "description": "Testing unauthenticated message listing.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    response = await client.get(f"/api/v1/tickets/{ticket_id}/messages")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_messages_on_closed_ticket_allowed(
    client: AsyncClient,
    customer_user: User,
    agent_user: User,
    sample_category: Category,
    auth_headers,
):
    # 1. Create ticket
    ticket_resp = await client.post(
        "/api/v1/tickets/",
        json={
            "title": "Closed ticket reading history",
            "description": "View message history of closed tickets.",
            "category_id": sample_category.id,
        },
        headers=auth_headers(customer_user),
    )
    ticket_id = ticket_resp.json()["id"]

    # 2. Add message while open
    await client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"content": "Important discussion before closure."},
        headers=auth_headers(customer_user),
    )

    # 3. Transition to CLOSED
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

    # 4. List messages on CLOSED ticket
    response = await client.get(
        f"/api/v1/tickets/{ticket_id}/messages",
        headers=auth_headers(customer_user),
    )
    assert response.status_code == 200
    messages = response.json()
    assert len(messages) == 1
    assert messages[0]["content"] == "Important discussion before closure."
