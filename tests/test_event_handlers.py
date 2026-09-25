from datetime import timedelta, date, time
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, Message, CallbackQuery
from telegram.ext import ContextTypes, ConversationHandler

from app.database.database import get_db
from app.database.models import EventScope, RecurrenceType, ReminderStatus
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.event_repo import EventRepository
from app.database.repositories.reminder_repo import ReminderRepository
from app.services.couple_service import CoupleService
from app.bot.handlers.event import (
    start_add_event,
    process_event_title,
    process_event_date,
    process_event_time,
    process_event_participant,
    process_event_recurrence,
    process_event_reminder,
    process_event_confirm,
    cancel_event,
)
from app.bot.states.event_states import (
    EVENT_TITLE,
    EVENT_DATE,
    EVENT_TIME,
    EVENT_PARTICIPANT,
    EVENT_RECURRENCE,
    EVENT_REMINDER,
    EVENT_CONFIRM,
)
from app.utils.date_utils import get_local_now


@pytest.mark.anyio
async def test_start_add_event_without_couple():
    with get_db() as session:
        UserRepository.create_or_update(session, telegram_id=77777, name="Solteiro")

    tg_user = TgUser(id=77777, first_name="Solteiro", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}

    state = await start_add_event(update, context)
    assert state == ConversationHandler.END
    sent_text = message.reply_text.call_args[0][0]
    assert "precisa estar conectado(a) em um casal" in sent_text


@pytest.mark.anyio
async def test_full_add_event_flow():
    # Cria casal de teste
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=88888, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=99999, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 88888)
        CoupleService.join_couple(session, 99999, code)

    tg_user = TgUser(id=88888, first_name="Douglas", is_bot=False)
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}
    context.bot.send_message = AsyncMock()

    # 1. Start /add
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None

    state = await start_add_event(update, context)
    assert state == EVENT_TITLE

    # 2. Título
    message.text = "Jantar Especial"
    state = await process_event_title(update, context)
    assert state == EVENT_DATE

    # 3. Data
    future_date = (get_local_now() + timedelta(days=3)).date()
    message.text = future_date.strftime("%d/%m/%Y")
    state = await process_event_date(update, context)
    assert state == EVENT_TIME

    # 4. Horário
    message.text = "20:00"
    state = await process_event_time(update, context)
    assert state == EVENT_PARTICIPANT

    # 5. Participante: Nós dois (SHARED)
    q_part = AsyncMock(spec=CallbackQuery)
    q_part.data = "scope_shared"
    q_part.answer = AsyncMock()
    q_part.edit_message_text = AsyncMock()
    u_part = MagicMock(spec=Update)
    u_part.callback_query = q_part
    state = await process_event_participant(u_part, context)
    assert state == EVENT_RECURRENCE

    # 6. Recorrência: Não se repete (NONE)
    q_rec = AsyncMock(spec=CallbackQuery)
    q_rec.data = "recur_none"
    q_rec.answer = AsyncMock()
    q_rec.edit_message_text = AsyncMock()
    u_rec = MagicMock(spec=Update)
    u_rec.callback_query = q_rec
    state = await process_event_recurrence(u_rec, context)
    assert state == EVENT_REMINDER

    # 7. Lembrete: 1 hora antes (60 min)
    q_rem = AsyncMock(spec=CallbackQuery)
    q_rem.data = "remind_60"
    q_rem.answer = AsyncMock()
    q_rem.edit_message_text = AsyncMock()
    u_rem = MagicMock(spec=Update)
    u_rem.callback_query = q_rem
    state = await process_event_reminder(u_rem, context)
    assert state == EVENT_CONFIRM
    summary_text = q_rem.edit_message_text.call_args[0][0]
    assert "Jantar Especial" in summary_text
    assert "1 hora antes" in summary_text

    # 8. Confirmação
    q_conf = AsyncMock(spec=CallbackQuery)
    q_conf.data = "confirm_event_save"
    q_conf.answer = AsyncMock()
    q_conf.edit_message_text = AsyncMock()
    u_conf = MagicMock(spec=Update)
    u_conf.callback_query = q_conf
    state = await process_event_confirm(u_conf, context)
    assert state == ConversationHandler.END
    confirm_text = q_conf.edit_message_text.call_args[0][0]
    assert "Evento criado!" in confirm_text

    # Notificou a parceira
    assert context.bot.send_message.called
    assert context.bot.send_message.call_args[1]["chat_id"] == 99999

    # Verifica no banco de dados se o evento e o lembrete foram persistidos
    with get_db() as session:
        events = EventRepository.list_upcoming(session, couple_id=context.user_data.get("couple_id", 1))
        assert len(events) == 1
        ev = events[0]
        assert ev.title == "Jantar Especial"
        assert ev.scope == EventScope.SHARED

        # Lembrete pendente criado
        pending = ReminderRepository.list_pending(session, current_time=ev.start_at)
        assert len(pending) == 1
        assert pending[0].event_id == ev.id
        assert pending[0].minutes_before == 60
        assert pending[0].status == ReminderStatus.PENDING
