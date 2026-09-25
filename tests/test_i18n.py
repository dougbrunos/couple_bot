import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, Message, CallbackQuery
from telegram.ext import ContextTypes

from app.database.database import get_db, init_db
from app.database.repositories.user_repo import UserRepository
from app.bot.handlers.start import (
    start_handler,
    set_language_callback_handler,
    language_prompt_handler,
    send_main_menu,
)
from app.bot.handlers.query_handlers import today_handler
from app.services.couple_service import CoupleService
from app.utils.i18n import t, get_user_language


def test_i18n_translation():
    assert t("btn_today", "en") == "☀️ Today"
    assert t("btn_today", "pt") == "☀️ Hoje"
    assert "Hello, John!" in t("welcome_title", "en", name="John")
    assert "Olá, John!" in t("welcome_title", "pt", name="John")


@pytest.mark.anyio
async def test_set_language_callback_en():
    init_db()

    tg_user = TgUser(id=999001, first_name="Alice", is_bot=False)
    query = AsyncMock(spec=CallbackQuery)
    query.data = "set_lang_en"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.callback_query = query
    update.message = None

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {}

    await set_language_callback_handler(update, context)

    assert query.answer.called
    assert query.edit_message_text.called
    sent_text = query.edit_message_text.call_args[0][0]
    assert "Hello, Alice!" in sent_text

    with get_db() as session:
        user = UserRepository.get_by_telegram_id(session, 999001)
        assert user is not None
        assert user.language == "en"


@pytest.mark.anyio
async def test_english_today_handler():
    init_db()
    with get_db() as session:
        u1 = UserRepository.create_or_update(
            session, telegram_id=888001, name="Bob", language="en"
        )
        code, _, _ = CoupleService.create_or_get_invite(session, 888001)
        u2 = UserRepository.create_or_update(
            session, telegram_id=888002, name="Carol", language="en"
        )
        CoupleService.join_couple(session, 888002, code)

    tg_user = TgUser(id=888001, first_name="Bob", is_bot=False)
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
    assert "TODAY" in sent_text
    assert "Free day" in sent_text
