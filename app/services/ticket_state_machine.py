from app.models.enums import TicketStatus


class TicketStateMachine:
    status_transition = {
        TicketStatus.OPEN: {TicketStatus.IN_PROGRESS},
        TicketStatus.IN_PROGRESS: {TicketStatus.OPEN, TicketStatus.RESOLVED},
        TicketStatus.RESOLVED: {TicketStatus.IN_PROGRESS, TicketStatus.CLOSED},
        TicketStatus.CLOSED: set(),
    }

    @classmethod
    def can_transition(
        cls,
        current: TicketStatus,
        new: TicketStatus,
    ) -> bool:
        return new in cls.status_transition.get(current, set())

    @classmethod
    def transition(
        cls,
        current: TicketStatus,
        new: TicketStatus,
    ) -> TicketStatus:

        if not cls.can_transition(current, new):
            raise ValueError(f"Invalid transition: {current.value} → {new.value}")

        return new
