from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Reminder, ReminderStatus, utc_now


class ReminderRepository:
    @staticmethod
    def create(
        session: Session,
        event_id: int,
        scheduled_at: datetime,
        minutes_before: int = 0,
        user_id: Optional[int] = None,
    ) -> Reminder:
        reminder = Reminder(
            event_id=event_id,
            user_id=user_id,
            minutes_before=minutes_before,
            scheduled_at=scheduled_at,
            status=ReminderStatus.PENDING,
        )
        session.add(reminder)
        session.flush()
        return reminder

    @staticmethod
    def get_by_id(session: Session, reminder_id: int) -> Optional[Reminder]:
        return session.query(Reminder).filter(Reminder.id == reminder_id).first()

    @staticmethod
    def list_pending(
        session: Session, current_time: Optional[datetime] = None
    ) -> List[Reminder]:
        """Busca lembretes pendentes cujo horário agendado seja menor ou igual a current_time."""
        if current_time is None:
            current_time = utc_now()

        return (
            session.query(Reminder)
            .filter(
                Reminder.status == ReminderStatus.PENDING,
                Reminder.scheduled_at <= current_time,
            )
            .order_by(Reminder.scheduled_at.asc())
            .all()
        )

    @staticmethod
    def mark_as_sent(
        session: Session, reminder_id: int, sent_at: Optional[datetime] = None
    ) -> bool:
        reminder = ReminderRepository.get_by_id(session, reminder_id)
        if not reminder:
            return False

        if sent_at is None:
            sent_at = utc_now()

        reminder.status = ReminderStatus.SENT
        reminder.sent_at = sent_at
        session.flush()
        return True

    @staticmethod
    def mark_as_cancelled(session: Session, reminder_id: int) -> bool:
        reminder = ReminderRepository.get_by_id(session, reminder_id)
        if not reminder:
            return False

        reminder.status = ReminderStatus.CANCELLED
        session.flush()
        return True

    @staticmethod
    def cancel_by_event_id(session: Session, event_id: int) -> int:
        """Cancela todos os lembretes pendentes de um evento."""
        updated = (
            session.query(Reminder)
            .filter(
                Reminder.event_id == event_id,
                Reminder.status == ReminderStatus.PENDING,
            )
            .update({"status": ReminderStatus.CANCELLED})
        )
        session.flush()
        return updated
