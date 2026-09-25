from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.database.models import Event, EventScope, RecurrenceType, utc_now


class EventRepository:
    @staticmethod
    def create(
        session: Session,
        couple_id: int,
        created_by: int,
        title: str,
        start_at: datetime,
        scope: EventScope = EventScope.PERSONAL,
        owner_id: Optional[int] = None,
        end_at: Optional[datetime] = None,
        description: Optional[str] = None,
        recurrence_type: RecurrenceType = RecurrenceType.NONE,
        recurrence_data: Optional[str] = None,
    ) -> Event:
        event = Event(
            couple_id=couple_id,
            created_by=created_by,
            owner_id=owner_id if owner_id else created_by,
            title=title.strip(),
            description=description.strip() if description else None,
            start_at=start_at,
            end_at=end_at,
            scope=scope,
            recurrence_type=recurrence_type,
            recurrence_data=recurrence_data,
        )
        session.add(event)
        session.flush()
        return event

    @staticmethod
    def get_by_id(session: Session, event_id: int) -> Optional[Event]:
        return session.query(Event).filter(Event.id == event_id).first()

    @staticmethod
    def list_by_period(
        session: Session,
        couple_id: int,
        start_dt: datetime,
        end_dt: datetime,
    ) -> List[Event]:
        """Lista eventos fixos que iniciam dentro de um intervalo de datas."""
        return (
            session.query(Event)
            .filter(
                Event.couple_id == couple_id,
                Event.start_at >= start_dt,
                Event.start_at <= end_dt,
            )
            .order_by(Event.start_at.asc())
            .all()
        )

    @staticmethod
    def list_all_active_by_couple(
        session: Session, couple_id: int
    ) -> List[Event]:
        """Lista todos os eventos do casal (inclusive recorrentes)."""
        return (
            session.query(Event)
            .filter(Event.couple_id == couple_id)
            .order_by(Event.start_at.asc())
            .all()
        )

    @staticmethod
    def list_upcoming(
        session: Session,
        couple_id: int,
        from_time: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Event]:
        """Lista os próximos eventos a partir de um momento."""
        if from_time is None:
            from_time = utc_now()

        return (
            session.query(Event)
            .filter(
                Event.couple_id == couple_id,
                Event.start_at >= from_time,
            )
            .order_by(Event.start_at.asc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def delete(session: Session, event_id: int) -> bool:
        event = EventRepository.get_by_id(session, event_id)
        if not event:
            return False
        session.delete(event)
        session.flush()
        return True
