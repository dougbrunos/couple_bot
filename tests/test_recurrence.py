from datetime import date, time, timedelta
import pytest

from app.database.database import get_db
from app.database.models import EventScope, RecurrenceType
from app.database.repositories.user_repo import UserRepository
from app.services.couple_service import CoupleService
from app.services.event_service import EventService


def test_recurrence_daily():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=90901, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=90902, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 90901)
        couple, _, _ = CoupleService.join_couple(session, 90902, code)

        start_date = date(2026, 9, 20)
        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Tomar Remédio",
            event_date=start_date,
            event_time=time(8, 0),
            recurrence_type=RecurrenceType.DAILY,
        )

        # Deve aparecer no dia de início
        events_start = EventService.get_events_for_date(session, couple.id, start_date)
        assert len(events_start) == 1

        # Deve aparecer 10 dias depois
        events_future = EventService.get_events_for_date(session, couple.id, start_date + timedelta(days=10))
        assert len(events_future) == 1
        assert events_future[0].title == "Tomar Remédio"

        # NÃO deve aparecer antes da data de início
        events_past = EventService.get_events_for_date(session, couple.id, start_date - timedelta(days=1))
        assert len(events_past) == 0


def test_recurrence_weekly():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=90903, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=90904, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 90903)
        couple, _, _ = CoupleService.join_couple(session, 90904, code)

        # Quinta-feira, 24/09/2026
        thursday = date(2026, 9, 24)
        assert thursday.weekday() == 3

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Futebol",
            event_date=thursday,
            event_time=time(20, 0),
            recurrence_type=RecurrenceType.WEEKLY,
        )

        # Na quinta-feira seguinte (01/10/2026) deve aparecer
        next_thursday = thursday + timedelta(days=7)
        events_next = EventService.get_events_for_date(session, couple.id, next_thursday)
        assert len(events_next) == 1
        assert events_next[0].title == "Futebol"

        # Na sexta-feira (25/09/2026) NÃO deve aparecer
        friday = thursday + timedelta(days=1)
        events_friday = EventService.get_events_for_date(session, couple.id, friday)
        assert len(events_friday) == 0


def test_recurrence_weekly_multi_days():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=90905, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=90906, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 90905)
        couple, _, _ = CoupleService.join_couple(session, 90906, code)

        # Terça e Quinta (weekday 1 e 3)
        start_date = date(2026, 9, 22)  # Terça
        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Academia",
            event_date=start_date,
            event_time=time(18, 30),
            recurrence_type=RecurrenceType.WEEKLY,
            recurrence_data="[1, 3]",
        )

        # Terça-feira seguinte
        next_tuesday = start_date + timedelta(days=7)
        ev_tue = EventService.get_events_for_date(session, couple.id, next_tuesday)
        assert len(ev_tue) == 1

        # Quinta-feira
        thursday = start_date + timedelta(days=2)
        ev_thu = EventService.get_events_for_date(session, couple.id, thursday)
        assert len(ev_thu) == 1

        # Quarta-feira (weekday 2) NÃO deve aparecer
        wednesday = start_date + timedelta(days=1)
        ev_wed = EventService.get_events_for_date(session, couple.id, wednesday)
        assert len(ev_wed) == 0


def test_recurrence_monthly_and_yearly():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=90907, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=90908, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 90907)
        couple, _, _ = CoupleService.join_couple(session, 90908, code)

        # Mensal todo dia 15
        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Pagar Aluguel",
            event_date=date(2026, 9, 15),
            event_time=time(10, 0),
            recurrence_type=RecurrenceType.MONTHLY,
        )

        # Anual todo dia 20 de Outubro
        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Aniversário de Namoro",
            event_date=date(2026, 10, 20),
            event_time=time(20, 0),
            recurrence_type=RecurrenceType.YEARLY,
        )

        # Outubro dia 15: deve ter o aluguel
        ev_oct_15 = EventService.get_events_for_date(session, couple.id, date(2026, 10, 15))
        assert len(ev_oct_15) == 1
        assert ev_oct_15[0].title == "Pagar Aluguel"

        # Outubro dia 20 de 2027 (1 ano depois): deve ter o aniversário
        ev_oct_20_2027 = EventService.get_events_for_date(session, couple.id, date(2027, 10, 20))
        assert len(ev_oct_20_2027) == 1
        assert ev_oct_20_2027[0].title == "Aniversário de Namoro"
