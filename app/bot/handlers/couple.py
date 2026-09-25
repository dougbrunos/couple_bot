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
from app.utils.i18n import t

logger = logging.getLogger(__name__)


async def create_couple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    user_lang = "pt"
    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if db_user:
            user_lang = getattr(db_user, "language", "pt") or "pt"
        invite_code, expires_at, status = CoupleService.create_or_get_invite(session, user.id)

    back_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_back_menu", user_lang), callback_data="menu_main")]]
    )

    if status == "ALREADY_PAIRED":
        text = t("status_paired", user_lang)
    elif status == "USER_NOT_FOUND":
        text = t("status_unpaired", user_lang)
    else:
        tz = pytz.timezone(config.TIMEZONE)
        local_expires = expires_at.astimezone(tz)
        formatted_expires = local_expires.strftime("%H:%M")
        text = t("invite_created", user_lang, code=invite_code, expires=formatted_expires)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=back_button, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=back_button, parse_mode="Markdown")


async def prompt_join_couple(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_lang = "pt"
    if user:
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                user_lang = getattr(db_user, "language", "pt") or "pt"

    cancel_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_cancel", user_lang), callback_data="cancel_join_couple")]]
    )
    text = t("invite_prompt_join", user_lang)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=cancel_button, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=cancel_button, parse_mode="Markdown")

    return AWAITING_INVITE_CODE


async def process_join_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user or not update.message or not update.message.text:
        return AWAITING_INVITE_CODE

    code_input = update.message.text.strip().upper()
    user_lang = "pt"

    with get_db() as session:
        db_user = UserRepository.create_or_update(
            session, telegram_id=user.id, name=user.first_name or "Parceira"
        )
        user_lang = getattr(db_user, "language", "pt") or "pt"
        couple, partner, status = CoupleService.join_couple(session, user.id, code_input)
        partner_telegram_id = partner.telegram_id if partner else None
        partner_lang = getattr(partner, "language", "pt") if partner else "pt"

    cancel_button = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_cancel", user_lang), callback_data="cancel_join_couple")]]
    )

    if status == "INVALID_OR_EXPIRED":
        await update.message.reply_text(t("invite_invalid", user_lang), reply_markup=cancel_button)
        return AWAITING_INVITE_CODE

    if status == "CANNOT_PAIR_SELF":
        await update.message.reply_text(t("invite_same_user", user_lang), reply_markup=cancel_button)
        return AWAITING_INVITE_CODE

    if status == "ALREADY_PAIRED":
        keyboard = get_main_menu_keyboard(is_paired=True, lang=user_lang)
        await update.message.reply_text(t("status_paired", user_lang), reply_markup=keyboard)
        return ConversationHandler.END

    keyboard = get_main_menu_keyboard(is_paired=True, lang=user_lang)
    await update.message.reply_text(
        t("couple_joined_success", user_lang), reply_markup=keyboard, parse_mode="Markdown"
    )

    if partner_telegram_id:
        partner_notify = t(
            "couple_partner_notified",
            partner_lang,
            name=user.first_name or "Seu parceiro(a)",
        )
        try:
            await context.bot.send_message(
                chat_id=partner_telegram_id,
                text=partner_notify,
                reply_markup=get_main_menu_keyboard(is_paired=True, lang=partner_lang),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify partner {partner_telegram_id}: {e}")

    return ConversationHandler.END


async def cancel_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    is_paired = False
    has_pending = False
    user_lang = "pt"
    if user:
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                user_lang = getattr(db_user, "language", "pt") or "pt"
                couple = CoupleRepository.get_by_user_id(session, db_user.id)
                is_paired = couple is not None and couple.user_2_id is not None
                has_pending = couple is not None and couple.user_2_id is None

    keyboard = get_main_menu_keyboard(
        is_paired=is_paired, has_pending_invite=has_pending, lang=user_lang
    )
    text = t("event_cancelled", user_lang)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)

    return ConversationHandler.END


def get_join_couple_conversation_handler() -> ConversationHandler:
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
