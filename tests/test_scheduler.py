from datetime import time, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope, ReminderStatus
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.reminder_repo import ReminderRepository
from app.services.couple_service import CoupleService
from app.services.event_service import EventService
from app.scheduler.scheduler import check_and_send_reminders
from app.bot.handlers.reminder_handlers import (
    reminder_ack_handler,
    reminder_snooze_menu_handler,
    reminder_snooze_execute_handler,
    reminder_snooze_cancel_handler,
)
from app.utils.date_utils import utc_now, get_local_now


@pytest.mark.anyio
async def test_scheduler_dispatches_pending_reminders():
    today = get_local_now().date()
    now_utc = utc_now()

    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=111222, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=333444, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 111222)
        couple, _, _ = CoupleService.join_couple(session, 333444, code)

        ev1, rem1 = EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Jantar a Dois",
            event_date=today,
            event_time=time(20, 0),
            scope=EventScope.SHARED,
            reminder_minutes=60,
        )
        rem1.scheduled_at = now_utc - timedelta(minutes=1)
        rem1_id = rem1.id

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    await check_and_send_reminders(context)

    assert context.bot.send_message.call_count == 2
    sent_text = context.bot.send_message.call_args_list[0][1]["text"]
    assert "LEMBRETE DO CASAL" in sent_text

    with get_db() as session:
        r1 = ReminderRepository.get_by_id(session, rem1_id)
        assert r1.status == ReminderStatus.SENT


@pytest.mark.anyio
async def test_reminder_ack_and_snooze():
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=555666, name="Douglas")
        code, _, _ = CoupleService.create_or_get_invite(session, 555666)
        u2 = UserRepository.create_or_update(session, telegram_id=777888, name="Namorada")
        couple, _, _ = CoupleService.join_couple(session, 777888, code)

        ev, rem = EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Dentista",
            event_date=today,
            event_time=time(14, 0),
            reminder_minutes=30,
        )
        rem_id = rem.id
        event_id = ev.id

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    # 1. Teste de confirmação (OK)
    q_ack = AsyncMock(spec=CallbackQuery)
    q_ack.data = f"rem_ack_{rem_id}"
    q_ack.message = MagicMock(spec=Message)
    q_ack.message.text = "🔔 Dentista às 14:00"
    q_ack.answer = AsyncMock()
    q_ack.edit_message_text = AsyncMock()
    u_ack = MagicMock(spec=Update)
    u_ack.callback_query = q_ack

    await reminder_ack_handler(u_ack, context)
    assert q_ack.edit_message_text.called
    assert "Confirmado" in q_ack.edit_message_text.call_args[1]["text"]

    # 2. Teste de menu de adiamento
    q_snooze_menu = AsyncMock(spec=CallbackQuery)
    q_snooze_menu.data = f"rem_snooze_{rem_id}"
    q_snooze_menu.message = MagicMock(spec=Message)
    q_snooze_menu.message.text = "🔔 Dentista às 14:00"
    q_snooze_menu.answer = AsyncMock()
    q_snooze_menu.edit_message_text = AsyncMock()
    u_snooze_menu = MagicMock(spec=Update)
    u_snooze_menu.callback_query = q_snooze_menu

    await reminder_snooze_menu_handler(u_snooze_menu, context)
    assert q_snooze_menu.edit_message_text.called
    assert "Adiar para quando?" in q_snooze_menu.edit_message_text.call_args[1]["text"]

    # 3. Teste de execução de adiamento (10 min)
    q_snooze_exec = AsyncMock(spec=CallbackQuery)
    q_snooze_exec.data = f"snooze_do_{rem_id}_10"
    q_snooze_exec.message = MagicMock(spec=Message)
    q_snooze_exec.message.text = "🔔 Dentista às 14:00\n\n⏰ *Adiar para quando?*"
    q_snooze_exec.answer = AsyncMock()
    q_snooze_exec.edit_message_text = AsyncMock()
    u_snooze_exec = MagicMock(spec=Update)
    u_snooze_exec.callback_query = q_snooze_exec

    await reminder_snooze_execute_handler(u_snooze_exec, context)
    assert q_snooze_exec.edit_message_text.called
    assert "Adiado" in q_snooze_exec.edit_message_text.call_args[1]["text"]

    # Verifica se um novo lembrete com status PENDING foi criado
    with get_db() as session:
        pending = ReminderRepository.list_pending(session, current_time=utc_now() + timedelta(minutes=15))
        assert len(pending) == 1
        assert pending[0].event_id == event_id
        assert pending[0].minutes_before == 10
        assert pending[0].status == ReminderStatus.PENDING
