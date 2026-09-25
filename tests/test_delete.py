from datetime import time, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.event_repo import EventRepository
from app.services.couple_service import CoupleService
from app.services.event_service import EventService
from app.bot.handlers.delete_handlers import (
    delete_menu_handler,
    confirm_delete_prompt_handler,
    execute_delete_handler,
)
from app.utils.date_utils import get_local_now


@pytest.mark.anyio
async def test_delete_menu_empty():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=10101, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=20202, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 10101)
        CoupleService.join_couple(session, 20202, code)

    tg_user = TgUser(id=10101, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await delete_menu_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "Você não possui eventos futuros" in sent_text


@pytest.mark.anyio
async def test_delete_flow_and_confirmation():
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=30303, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=40404, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 30303)
        couple, _, _ = CoupleService.join_couple(session, 40404, code)

        ev, rem = EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Dentista",
            event_date=today + timedelta(days=2),
            event_time=time(14, 0),
            scope=EventScope.SHARED,
            reminder_minutes=60,
        )
        event_id = ev.id

    tg_user = TgUser(id=30303, first_name="Douglas", is_bot=False)
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    # 1. Clica no evento para confirmar
    q_sel = AsyncMock(spec=CallbackQuery)
    q_sel.data = f"del_sel_{event_id}"
    q_sel.answer = AsyncMock()
    q_sel.edit_message_text = AsyncMock()
    u_sel = MagicMock(spec=Update)
    u_sel.effective_user = tg_user
    u_sel.callback_query = q_sel

    await confirm_delete_prompt_handler(u_sel, context)
    assert q_sel.edit_message_text.called
    confirm_text = q_sel.edit_message_text.call_args[0][0]
    assert "Excluir este evento?" in confirm_text
    assert "Dentista" in confirm_text

    # 2. Confirma exclusão definitiva
    q_del = AsyncMock(spec=CallbackQuery)
    q_del.data = f"del_confirm_{event_id}"
    q_del.answer = AsyncMock()
    q_del.edit_message_text = AsyncMock()
    u_del = MagicMock(spec=Update)
    u_del.effective_user = tg_user
    u_del.callback_query = q_del

    await execute_delete_handler(u_del, context)
    assert q_del.edit_message_text.called
    deleted_text = q_del.edit_message_text.call_args[0][0]
    assert "Evento excluído." in deleted_text

    # Verifica se notificou a parceira sobre o evento compartilhado
    assert context.bot.send_message.called
    assert context.bot.send_message.call_args[1]["chat_id"] == 40404

    # Verifica se sumiu do banco de dados
    with get_db() as session:
        assert EventRepository.get_by_id(session, event_id) is None


@pytest.mark.anyio
async def test_delete_security_isolation():
    # Casal A cria evento
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=50505, name="Douglas")
        code, _, _ = CoupleService.create_or_get_invite(session, 50505)
        u2 = UserRepository.create_or_update(session, telegram_id=60606, name="Namorada")
        couple_a, _, _ = CoupleService.join_couple(session, 60606, code)

        ev, _ = EventService.create_event(
            session=session,
            couple_id=couple_a.id,
            created_by=u1.id,
            title="Segredo de Casal",
            event_date=today + timedelta(days=2),
            event_time=time(14, 0),
        )
        event_id = ev.id

        # Usuário B (de outro casal)
        u3 = UserRepository.create_or_update(session, telegram_id=70707, name="Outro")

    # Usuário B tenta confirmar/excluir evento do Casal A
    tg_user_b = TgUser(id=70707, first_name="Outro", is_bot=False)
    q_hacker = AsyncMock(spec=CallbackQuery)
    q_hacker.data = f"del_confirm_{event_id}"
    q_hacker.answer = AsyncMock()
    q_hacker.edit_message_text = AsyncMock()
    u_hacker = MagicMock(spec=Update)
    u_hacker.effective_user = tg_user_b
    u_hacker.callback_query = q_hacker
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await execute_delete_handler(u_hacker, context)
    assert q_hacker.edit_message_text.called
    err_text = q_hacker.edit_message_text.call_args[0][0]
    assert "não encontrado ou já excluído" in err_text

    # Evento permanece intacto no banco
    with get_db() as session:
        assert EventRepository.get_by_id(session, event_id) is not None
