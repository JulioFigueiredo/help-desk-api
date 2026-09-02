from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.api.v1.dependencies import get_db
from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.main import app
from app.models.category import Category
from app.models.user import User, UserRole


@pytest.fixture
async def db_engine():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def user_factory(db_session: AsyncSession):
    async def _create_user(
        email: str = "customer@example.com",
        password: str = "securepassword123",
        name: str = "Test User",
        role: UserRole = UserRole.CUSTOMER,
        is_active: bool = True,
    ) -> User:
        user = User(
            email=email,
            hashed_password=hash_password(password),
            name=name,
            role=role,
            is_active=is_active,
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
async def customer_user(user_factory) -> User:
    return await user_factory(
        email="customer@example.com",
        name="Customer User",
        role=UserRole.CUSTOMER,
    )


@pytest.fixture
async def agent_user(user_factory) -> User:
    return await user_factory(
        email="agent@example.com",
        name="Agent User",
        role=UserRole.AGENT,
    )


@pytest.fixture
async def admin_user(user_factory) -> User:
    return await user_factory(
        email="admin@example.com",
        name="Admin User",
        role=UserRole.ADMIN,
    )


@pytest.fixture
async def inactive_user(user_factory) -> User:
    return await user_factory(
        email="inactive@example.com",
        name="Inactive User",
        role=UserRole.CUSTOMER,
        is_active=False,
    )


@pytest.fixture
def auth_headers():
    def _auth_headers(user: User) -> dict[str, str]:
        token = create_access_token(subject=user.id, role=user.role)
        return {"Authorization": f"Bearer {token}"}

    return _auth_headers


@pytest.fixture
def category_factory(db_session: AsyncSession):
    async def _create_category(
        name: str = "Technical Support",
        description: str | None = "Technical issues and bugs",
    ) -> Category:
        category = Category(name=name, description=description)
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category

    return _create_category


@pytest.fixture
async def sample_category(category_factory) -> Category:
    return await category_factory()
