import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
import pytz

from app.config import config
from app.database.database import get_db
from app.database.repositories.user_repo import UserRepository
from app.services.couple_service import CoupleService
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.bot.states.couple_states import AWAITING_INVITE_CODE

logger = logging.getLogger(__name__)


async def create_couple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler acionado ao clicar em 'Criar casal' ou /criar_casal."""
    user = update.effective_user
    if not user:
        return

    with get_db() as session:
        invite_code, expires_at, status = CoupleService.create_or_get_invite(session, user.id)

    back_button = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu_main")]])

    if status == "ALREADY_PAIRED":
        text = "❤️ Vocês já estão vinculados como um casal! Use as opções do menu para gerenciar seus compromissos."
    elif status == "USER_NOT_FOUND":
        text = "⚠️ Usuário não encontrado. Digite /start para iniciar seu cadastro."
    else:
        tz = pytz.timezone(config.TIMEZONE)
        local_expires = expires_at.astimezone(tz)
        formatted_expires = local_expires.strftime("%H:%M")

        text = "❤️ *Convite criado com sucesso!*\n\n"
        text += "Envie este código para sua namorada:\n\n"
        text += f"`{invite_code}`\n\n"
        text += f"⏳ O código expira em 30 minutos (às {formatted_expires}).\n\n"
        text += "Ela só precisa abrir este bot e escolher *'Entrar em um casal'*."

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=back_button, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=back_button, parse_mode="Markdown")


async def prompt_join_couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia o fluxo guiado para entrar em um casal."""
    cancel_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_join_couple")]]
    )
    text = "❤️ *Entrar em um casal*\n\n"
    text += "Digite o código do convite enviado pelo seu parceiro(a):\n"
    text += "Exemplo: `CASAL-7X42`"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=cancel_button, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=cancel_button, parse_mode="Markdown")

    return AWAITING_INVITE_CODE


async def process_join_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Recebe e processa o código de convite digitado."""
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return AWAITING_INVITE_CODE

    code_input = update.message.text.strip().upper()

    with get_db() as session:
        # Garante que o usuário que está digitando está cadastrado
        UserRepository.create_or_update(session, telegram_id=user.id, name=user.first_name or "Parceira")
        couple, partner, status = CoupleService.join_couple(session, user.id, code_input)
        partner_telegram_id = partner.telegram_id if partner else None
        partner_name = partner.name if partner else None

    cancel_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_join_couple")]]
    )

    if status == "INVALID_OR_EXPIRED":
        await update.message.reply_text(
            "⚠️ Código inválido ou expirado. Verifique o código com seu parceiro(a) e tente novamente:",
            reply_markup=cancel_button,
        )
        return AWAITING_INVITE_CODE

    if status == "CANNOT_PAIR_SELF":
        await update.message.reply_text(
            "⚠️ Você não pode usar o código de convite gerado por você mesmo. Envie o código para o seu parceiro(a):",
            reply_markup=cancel_button,
        )
        return AWAITING_INVITE_CODE

    if status == "ALREADY_PAIRED":
        keyboard = get_main_menu_keyboard(is_paired=True)
        await update.message.reply_text(
            "❤️ Você já está vinculado(a) a um casal!",
            reply_markup=keyboard,
        )
        return ConversationHandler.END

    # Conexão realizada com sucesso!
    keyboard = get_main_menu_keyboard(is_paired=True)
    success_text = "❤️ *Conexão realizada com sucesso!*\n\nAgora vocês podem criar eventos pessoais ou compartilhados."
    await update.message.reply_text(success_text, reply_markup=keyboard, parse_mode="Markdown")

    # Notifica o parceiro (User 1)
    if partner_telegram_id:
        partner_notify = (
            f"❤️ *Conexão realizada!*\n\n"
            f"*{user.first_name or 'Seu parceiro(a)'}* acabou de se conectar ao seu espaço de casal!\n"
            f"Agora vocês podem organizar compromissos juntos."
        )
        try:
            await context.bot.send_message(
                chat_id=partner_telegram_id,
                text=partner_notify,
                reply_markup=get_main_menu_keyboard(is_paired=True),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Não foi possível notificar o parceiro {partner_telegram_id}: {e}")

    return ConversationHandler.END


async def cancel_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancela o processo de entrar no casal e volta ao menu."""
    user = update.effective_user
    is_paired = False
    has_pending = False
    if user:
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                couple = CoupleRepository.get_by_user_id(session, db_user.id)
                is_paired = couple is not None and couple.user_2_id is not None
                has_pending = couple is not None and couple.user_2_id is None

    keyboard = get_main_menu_keyboard(is_paired=is_paired, has_pending_invite=has_pending)
    text = "Operação cancelada. De volta ao menu principal:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)

    return ConversationHandler.END


def get_join_couple_conversation_handler() -> ConversationHandler:
    """Retorna o ConversationHandler configurado para o fluxo de entrada de casal."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(prompt_join_couple, pattern="^menu_join_couple$"),
            CommandHandler(["entrar_casal", "entrar", "join_couple", "join"], prompt_join_couple),
        ],
        states={
            AWAITING_INVITE_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_join_code),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_join, pattern="^cancel_join_couple$"),
            CommandHandler(["cancelar", "cancel"], cancel_join),
        ],
        per_message=False,
    )
