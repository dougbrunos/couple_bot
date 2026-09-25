from datetime import time, timedelta
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope, RecurrenceType
from app.database.repositories.user_repo import UserRepository
from app.services.couple_service import CoupleService
from app.services.event_service import EventService
from app.bot.handlers.query_handlers import today_handler, week_handler, events_list_handler
from app.utils.date_utils import get_local_now


@pytest.mark.anyio
async def test_today_handler_empty():
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=12121, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=23232, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 12121)
        CoupleService.join_couple(session, 23232, code)

    tg_user = TgUser(id=12121, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await today_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "Nenhum compromisso registrado" in sent_text
    assert "Dia livre. 👍" in sent_text


@pytest.mark.anyio
async def test_today_handler_with_events():
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=34343, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=45454, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 34343)
        couple, _, _ = CoupleService.join_couple(session, 45454, code)

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Academia",
            event_date=today,
            event_time=time(18, 30),
            scope=EventScope.PERSONAL,
            owner_id=u1.id,
        )

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Faculdade",
            event_date=today,
            event_time=time(19, 0),
            scope=EventScope.PARTNER,
            owner_id=u2.id,
        )

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Jantar",
            event_date=today,
            event_time=time(20, 30),
            scope=EventScope.SHARED,
        )

    tg_user = TgUser(id=34343, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await today_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "DOUGLAS" in sent_text
    assert "18:30 — Academia" in sent_text
    assert "NAMORADA" in sent_text
    assert "19:00 — Faculdade" in sent_text
    assert "JUNTOS" in sent_text
    assert "20:30 — Jantar" in sent_text
    assert "Você tem 3 compromissos hoje." in sent_text


@pytest.mark.anyio
async def test_week_handler():
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=56565, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=67676, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 56565)
        couple, _, _ = CoupleService.join_couple(session, 67676, code)

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Dentista",
            event_date=today + timedelta(days=1),
            event_time=time(14, 0),
            scope=EventScope.PERSONAL,
            owner_id=u1.id,
        )

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Cinema",
            event_date=today + timedelta(days=2),
            event_time=time(20, 0),
            scope=EventScope.SHARED,
        )

    tg_user = TgUser(id=56565, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await week_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "PRÓXIMOS 7 DIAS" in sent_text
    assert "14:00 — Dentista — 👤 Douglas" in sent_text
    assert "20:00 — Cinema — ❤️ Nós dois" in sent_text
    assert "Nenhum evento." in sent_text


@pytest.mark.anyio
async def test_events_list_handler():
    today = get_local_now().date()
    with get_db() as session:
        u1 = UserRepository.create_or_update(session, telegram_id=78787, name="Douglas")
        u2 = UserRepository.create_or_update(session, telegram_id=89898, name="Namorada")
        code, _, _ = CoupleService.create_or_get_invite(session, 78787)
        couple, _, _ = CoupleService.join_couple(session, 89898, code)

        EventService.create_event(
            session=session,
            couple_id=couple.id,
            created_by=u1.id,
            title="Show de Música",
            event_date=today + timedelta(days=4),
            event_time=time(21, 0),
            scope=EventScope.SHARED,
        )

    tg_user = TgUser(id=78787, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await events_list_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "PRÓXIMOS EVENTOS" in sent_text
    assert "1. *Show de Música*" in sent_text
    assert "21:00" in sent_text
    assert "❤️ Nós dois" in sent_text
