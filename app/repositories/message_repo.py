from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, message: Message) -> Message:
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message, attribute_names=["author"])
        return message

    async def list_by_ticket(self, ticket_id: int) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.ticket_id == ticket_id)
            .options(selectinload(Message.author))
            .order_by(Message.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
