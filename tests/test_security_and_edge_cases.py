from datetime import time, timedelta, datetime
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope, ReminderStatus
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.database.repositories.event_repo import EventRepository
from app.database.repositories.reminder_repo import ReminderRepository
from app.services.couple_service import CoupleService
from app.services.event_service import EventService
from app.bot.handlers.query_handlers import today_handler, events_list_handler
from app.scheduler.scheduler import check_and_send_reminders
from app.utils.date_utils import (
    utc_now,
    get_local_now,
    parse_date_input,
    parse_time_input,
)


@pytest.mark.anyio
async def test_cross_couple_data_isolation():
    today = get_local_now().date()
    with get_db() as session:
        # Casal 1
        u1_c1 = UserRepository.create_or_update(session, telegram_id=1001, name="Douglas")
        u2_c1 = UserRepository.create_or_update(session, telegram_id=1002, name="Namorada 1")
        code1, _, _ = CoupleService.create_or_get_invite(session, 1001)
        couple1, _, _ = CoupleService.join_couple(session, 1002, code1)

        # Evento de hoje
        EventService.create_event(
            session=session,
            couple_id=couple1.id,
            created_by=u1_c1.id,
            title="Evento Exclusivo Casal 1 Hoje",
            event_date=today,
            event_time=time(23, 59),
            scope=EventScope.SHARED,
        )

        # Evento futuro de amanhã
        EventService.create_event(
            session=session,
            couple_id=couple1.id,
            created_by=u1_c1.id,
            title="Evento Exclusivo Casal 1 Amanhã",
            event_date=today + timedelta(days=1),
            event_time=time(14, 0),
            scope=EventScope.SHARED,
        )

        # Casal 2
        u1_c2 = UserRepository.create_or_update(session, telegram_id=2001, name="Outro Homem")
        u2_c2 = UserRepository.create_or_update(session, telegram_id=2002, name="Outra Mulher")
        code2, _, _ = CoupleService.create_or_get_invite(session, 2001)
        couple2, _, _ = CoupleService.join_couple(session, 2002, code2)

        EventService.create_event(
            session=session,
            couple_id=couple2.id,
            created_by=u1_c2.id,
            title="Evento Secreto Casal 2",
            event_date=today + timedelta(days=1),
            event_time=time(14, 0),
            scope=EventScope.SHARED,
        )

    # Douglas consulta /hoje
    tg_user = TgUser(id=1001, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await today_handler(update, context)
    sent_text = message.reply_text.call_args[0][0]
    assert "Evento Exclusivo Casal 1 Hoje" in sent_text
    assert "Evento Secreto Casal 2" not in sent_text

    # Douglas consulta /eventos
    await events_list_handler(update, context)
    sent_text_events = message.reply_text.call_args[0][0]
    assert "Evento Exclusivo Casal 1 Amanhã" in sent_text_events
    assert "Evento Secreto Casal 2" not in sent_text_events


def test_invite_expired_and_already_joined():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=3001, name="User A")
        u2 = UserRepository.create_or_update(session, telegram_id=3002, name="User B")
        u3 = UserRepository.create_or_update(session, telegram_id=3003, name="User C")

        # 1. Convite expirado
        code, expires, _ = CoupleService.create_or_get_invite(session, 3001)
        couple = CoupleRepository.get_by_user_id(session, u1.id)
        couple.invite_expires_at = utc_now() - timedelta(minutes=5)
        session.flush()

        _, _, status_exp = CoupleService.join_couple(session, 3002, code)
        assert status_exp == "INVALID_OR_EXPIRED"

        # 2. Reativa convite e conecta User B
        couple.invite_expires_at = utc_now() + timedelta(minutes=30)
        session.flush()
        _, _, status_ok = CoupleService.join_couple(session, 3002, code)
        assert status_ok == "OK"

        # 3. User C tenta reutilizar o mesmo convite
        _, _, status_reuse = CoupleService.join_couple(session, 3003, code)
        assert status_reuse == "INVALID_OR_EXPIRED"


def test_date_and_time_parser_edge_cases():
    # Data inexistente no calendário (31 de fevereiro)
    parsed_date, err = parse_date_input("31/02/2026")
    assert parsed_date is None
    assert "Data inválida" in err

    # Texto arbitrário
    parsed_date, err = parse_date_input("amanhã cedo")
    assert parsed_date is None
    assert "Formato inválido" in err

    # Horários inválidos
    parsed_time, err = parse_time_input("25:00")
    assert parsed_time is None
    assert "Horário inválido" in err

    parsed_time, err = parse_time_input("12:60")
    assert parsed_time is None
    assert "Horário inválido" in err

    parsed_time, err = parse_time_input("hora do almoço")
    assert parsed_time is None
    assert "Formato inválido" in err


@pytest.mark.anyio
async def test_cascading_deletion_of_reminders():
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=4001, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=4002, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 4001)
        couple, _, _ = CoupleService.join_couple(session, 4002, code)

        ev, rem = EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Evento Cancelado",
            event_date=today,
            event_time=time(18, 0),
            reminder_minutes=60,
        )
        rem.scheduled_at = utc_now() - timedelta(minutes=1)
        event_id = ev.id

        # Deleta o evento
        EventRepository.delete(session, event_id)

    # Executa o scheduler
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    await check_and_send_reminders(context)

    # Nenhuma mensagem deve ter sido enviada pois os lembretes foram removidos/cancelados
    assert not context.bot.send_message.called
