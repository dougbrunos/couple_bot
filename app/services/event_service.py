import json
from dataclasses import dataclass
from datetime import date, time, timedelta, datetime
from typing import Optional, Tuple, List
from sqlalchemy.orm import Session

from app.database.models import Event, Reminder, EventScope, RecurrenceType
from app.database.repositories.event_repo import EventRepository
from app.database.repositories.reminder_repo import ReminderRepository
from app.utils.date_utils import combine_to_utc, to_local_tz, get_local_now


@dataclass
class EventView:
    id: int
    title: str
    scope: EventScope
    owner_id: Optional[int]
    local_date: date
    local_time: time
    recurrence_type: RecurrenceType = RecurrenceType.NONE


class EventService:
    @staticmethod
    def create_event(
        session: Session,
        couple_id: int,
        created_by: int,
        title: str,
        event_date: date,
        event_time: time,
        scope: EventScope = EventScope.PERSONAL,
        owner_id: Optional[int] = None,
        recurrence_type: RecurrenceType = RecurrenceType.NONE,
        recurrence_data: Optional[str] = None,
        reminder_minutes: Optional[int] = None,
        description: Optional[str] = None,
    ) -> Tuple[Event, Optional[Reminder]]:
        """Cria o evento e agenda o lembrete associado."""
        start_at_utc = combine_to_utc(event_date, event_time)

        event = EventRepository.create(
            session=session,
            couple_id=couple_id,
            created_by=created_by,
            title=title,
            start_at=start_at_utc,
            scope=scope,
            owner_id=owner_id,
            recurrence_type=recurrence_type,
            recurrence_data=recurrence_data,
            description=description,
        )

        reminder = None
        if reminder_minutes is not None and reminder_minutes > 0:
            scheduled_at_utc = start_at_utc - timedelta(minutes=reminder_minutes)
            target_user_id = None if scope == EventScope.SHARED else (owner_id or created_by)

            reminder = ReminderRepository.create(
                session=session,
                event_id=event.id,
                scheduled_at=scheduled_at_utc,
                minutes_before=reminder_minutes,
                user_id=target_user_id,
            )

        return event, reminder

    @staticmethod
    def get_events_for_date(
        session: Session, couple_id: int, target_date: date
    ) -> List[EventView]:
        """Retorna todos os eventos que ocorrem na target_date como EventViews desacoplados."""
        all_events = EventRepository.list_all_active_by_couple(session, couple_id)
        matching: List[EventView] = []

        for ev in all_events:
            local_dt = to_local_tz(ev.start_at)
            ev_date = local_dt.date()
            ev_time = local_dt.time()

            # Eventos só ocorrem a partir da sua data inicial
            if ev_date > target_date:
                continue

            applies = False
            if ev.recurrence_type == RecurrenceType.NONE:
                applies = (ev_date == target_date)
            elif ev.recurrence_type == RecurrenceType.DAILY:
                applies = True
            elif ev.recurrence_type == RecurrenceType.WEEKLY:
                # Se houver dias específicos gravados em recurrence_data (ex: [1, 3] = ter, qui)
                if ev.recurrence_data:
                    try:
                        days = json.loads(ev.recurrence_data)
                        applies = target_date.weekday() in days
                    except Exception:
                        applies = (target_date.weekday() == ev_date.weekday())
                else:
                    applies = (target_date.weekday() == ev_date.weekday())
            elif ev.recurrence_type == RecurrenceType.MONTHLY:
                # Repete no mesmo dia do mês (ou no último dia do mês se o mês tiver menos dias)
                if target_date.day == ev_date.day:
                    applies = True
                elif ev_date.day > 28:
                    # Ajuste para meses com menos dias que o mês de criação
                    next_month = target_date.replace(day=28) + timedelta(days=4)
                    last_day_of_month = (next_month - timedelta(days=next_month.day)).day
                    if target_date.day == last_day_of_month and ev_date.day >= last_day_of_month:
                        applies = True
            elif ev.recurrence_type == RecurrenceType.YEARLY:
                # Repete no mesmo dia e mês todo ano
                if target_date.month == ev_date.month and target_date.day == ev_date.day:
                    applies = True
                elif ev_date.month == 2 and ev_date.day == 29 and target_date.month == 2 and target_date.day == 28:
                    # Anos não bissextos para aniversários em 29/fev
                    applies = True

            if applies:
                matching.append(
                    EventView(
                        id=ev.id,
                        title=ev.title,
                        scope=ev.scope,
                        owner_id=ev.owner_id,
                        local_date=target_date,
                        local_time=ev_time,
                        recurrence_type=ev.recurrence_type,
                    )
                )

        matching.sort(key=lambda item: item.local_time)
        return matching
