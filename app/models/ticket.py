from sqlalchemy.orm import relationship
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import TicketPriority, TicketStatus

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[TicketStatus] = mapped_column(
        SQLEnum(TicketStatus, name="ticket_status_enum"),
        default=TicketStatus.OPEN,
        nullable=False,
        index=True,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        SQLEnum(TicketPriority, name="ticket_priority_enum"),
        default=TicketPriority.MEDIUM,
        nullable=False,
        index=True,
    )
    customer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False, index=True
    )
    agent_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True, default=None, index=True
    )
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    category: Mapped["Category"] = relationship(back_populates="tickets")
    customer: Mapped["User"] = relationship(foreign_keys=[customer_id])
    agent: Mapped["User | None"] = relationship(foreign_keys=[agent_id])
