import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Message, Update, CallbackQuery
from telegram.ext import ContextTypes

from app.database.database import init_db, get_db
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.bot.handlers.start import start_handler
from app.bot.handlers.help import help_handler
from main import create_app


@pytest.mark.anyio
async def test_start_handler_creates_user():
    init_db()

    tg_user = TgUser(id=987654321, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await start_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "Olá, Douglas!" in sent_text
    assert "assistente de organização" in sent_text

    with get_db() as session:
        user = UserRepository.get_by_telegram_id(session, 987654321)
        assert user is not None
        assert user.name == "Douglas"


@pytest.mark.anyio
async def test_help_handler():
    init_db()

    tg_user = TgUser(id=987654321, first_name="Douglas", is_bot=False)
    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await help_handler(update, context)

    assert message.reply_text.called
    sent_text = message.reply_text.call_args[0][0]
    assert "Guia de Uso" in sent_text
    assert "/start" in sent_text


@pytest.mark.anyio
async def test_start_callback_query():
    init_db()

    tg_user = TgUser(id=987654321, first_name="Douglas", is_bot=False)
    query = AsyncMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = None
    update.callback_query = query

    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    await start_handler(update, context)

    assert query.answer.called
    assert query.edit_message_text.called
    sent_text = query.edit_message_text.call_args[0][0]
    assert "Olá, Douglas!" in sent_text


def test_create_app():
    app = create_app()
    assert app is not None

    # Verifica comandos registrados nos handlers
    commands = set()
    for handler_list in app.handlers.values():
        for handler in handler_list:
            if hasattr(handler, "commands"):
                commands.update(handler.commands)

    # Verifica comandos em portugues e ingles
    assert "start" in commands
    assert "menu" in commands
    assert "ajuda" in commands
    assert "help" in commands
    assert "hoje" in commands
    assert "today" in commands
    assert "semana" in commands
    assert "week" in commands
    assert "eventos" in commands
    assert "events" in commands
    assert "delete" in commands
    assert "remove" in commands
    assert "criar_casal" in commands
    assert "create_couple" in commands
