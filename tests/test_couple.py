import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import User as TgUser, Update, CallbackQuery, Message
from telegram.ext import ContextTypes, ConversationHandler

from app.database.database import init_db, get_db
from app.database.models import utc_now
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.services.couple_service import CoupleService
from app.bot.handlers.couple import (
    create_couple_handler,
    prompt_join_couple,
    process_join_code,
    cancel_join,
)
from app.bot.states.couple_states import AWAITING_INVITE_CODE


@pytest.mark.anyio
async def test_create_invite_service():
    init_db()
    with get_db() as session:
        UserRepository.create_or_update(session, telegram_id=55555, name="Douglas")
        code, expires_at, status = CoupleService.create_or_get_invite(session, 55555)
        assert status == "OK"
        assert code.startswith("CASAL-")
        assert expires_at > utc_now()

        # Chamada repetida deve retornar o mesmo código ativo
        code2, expires_at2, status2 = CoupleService.create_or_get_invite(session, 55555)
        assert code2 == code
        assert expires_at2 == expires_at


@pytest.mark.anyio
async def test_join_couple_service_and_handler():
    init_db()
    # 1. Usuário 1 cria convite
    with get_db() as session:
        UserRepository.create_or_update(session, telegram_id=11111, name="Douglas")
        code, _, _ = CoupleService.create_or_get_invite(session, 11111)

    # 2. Usuário 2 inicia o fluxo
    tg_user_2 = TgUser(id=22222, first_name="Namorada", is_bot=False)
    query = AsyncMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update_prompt = MagicMock(spec=Update)
    update_prompt.effective_user = tg_user_2
    update_prompt.message = None
    update_prompt.callback_query = query
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot.send_message = AsyncMock()

    state = await prompt_join_couple(update_prompt, context)
    assert state == AWAITING_INVITE_CODE
    assert query.edit_message_text.called

    # 3. Usuário 2 digita o código correto
    message_input = AsyncMock(spec=Message)
    message_input.text = code
    message_input.reply_text = AsyncMock()

    update_msg = MagicMock(spec=Update)
    update_msg.effective_user = tg_user_2
    update_msg.message = message_input
    update_msg.callback_query = None

    result_state = await process_join_code(update_msg, context)
    assert result_state == ConversationHandler.END
    assert message_input.reply_text.called
    sent_text = message_input.reply_text.call_args[0][0]
    assert "Conexão realizada com sucesso!" in sent_text

    # Verifica se o parceiro (User 1) recebeu notificação
    assert context.bot.send_message.called
    partner_chat_id = context.bot.send_message.call_args[1]["chat_id"]
    assert partner_chat_id == 11111

    # Verifica no banco de dados se estão unidos
    with get_db() as session:
        u1 = UserRepository.get_by_telegram_id(session, 11111)
        u2 = UserRepository.get_by_telegram_id(session, 22222)
        couple = CoupleRepository.get_by_user_id(session, u1.id)
        assert couple is not None
        assert couple.user_1_id == u1.id
        assert couple.user_2_id == u2.id


@pytest.mark.anyio
async def test_join_couple_invalid_code():
    init_db()
    tg_user = TgUser(id=33333, first_name="Outro", is_bot=False)
    message = AsyncMock(spec=Message)
    message.text = "CASAL-INVALIDO"
    message.reply_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = message
    update.callback_query = None
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    state = await process_join_code(update, context)
    assert state == AWAITING_INVITE_CODE
    sent_text = message.reply_text.call_args[0][0]
    assert "Código inválido ou expirado" in sent_text


@pytest.mark.anyio
async def test_cancel_join():
    init_db()
    tg_user = TgUser(id=44444, first_name="Teste", is_bot=False)
    query = AsyncMock(spec=CallbackQuery)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.effective_user = tg_user
    update.message = None
    update.callback_query = query
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

    state = await cancel_join(update, context)
    assert state == ConversationHandler.END
    assert query.edit_message_text.called
