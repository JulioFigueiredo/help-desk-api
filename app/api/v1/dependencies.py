from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User, UserRole
from app.repositories.user_repo import UserRepository

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)

    if not payload or payload.get("type") != "access" or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(payload["sub"])
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = await UserRepository(db).get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return current_user


class RoleChecker:
    """RBAC permission controller based on a callable class.

    Allows parameterizing allowed roles during initialization (__init__)
    and automatically validating the user during incoming HTTP requests via __call__.
    """

    def __init__(self, allowed_roles: list[UserRole]):
        self.allowed_roles = allowed_roles

    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
    ) -> User:
        """Make the class instance callable as a FastAPI dependency.

        Executed on every HTTP request by FastAPI's dependency injection system:
        1. Injects the authenticated active user via get_current_active_user.
        2. Validates whether the user's role is within the allowed roles list.

        Returns the User instance if authorized, otherwise raises HTTP 403 Forbidden.
        """
        if current_user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user


# RBAC shortcut dependencies
require_admin = RoleChecker([UserRole.ADMIN])
require_agent = RoleChecker([UserRole.AGENT])
require_staff = RoleChecker([UserRole.AGENT, UserRole.ADMIN])
require_customer = RoleChecker([UserRole.CUSTOMER])

__all__ = [
    "RoleChecker",
    "get_current_active_user",
    "get_current_user",
    "get_db",
    "oauth2_scheme",
    "require_admin",
    "require_agent",
    "require_customer",
    "require_staff",
]
