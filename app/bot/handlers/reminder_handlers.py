import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.repositories.user_repo import UserRepository
from app.utils.date_utils import utc_now, to_local_tz
from app.scheduler.scheduler import get_reminder_action_keyboard
from app.utils.i18n import t

logger = logging.getLogger(__name__)


async def reminder_ack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return

    user = update.effective_user
    user_lang = "pt"
    if user and isinstance(getattr(user, "id", None), int):
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                user_lang = getattr(db_user, "language", "pt") or "pt"

    ack_text = t("rem_ack_success", user_lang)
    await query.answer(ack_text)
    current_text = query.message.text if query.message else ""
    updated_text = f"{current_text}\n\n✓ *{ack_text.replace('✓', '').strip()}*"
    await query.edit_message_text(text=updated_text, reply_markup=None, parse_mode="Markdown")


async def reminder_snooze_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    reminder_id = int(query.data.replace("rem_snooze_", ""))

    user = update.effective_user
    user_lang = "pt"
    if user and isinstance(getattr(user, "id", None), int):
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                user_lang = getattr(db_user, "language", "pt") or "pt"

    h1_label = "1 hour" if user_lang == "en" else "1 hora"
    cancel_label = t("btn_cancel", user_lang)

    snooze_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10 min", callback_data=f"snooze_do_{reminder_id}_10"),
            InlineKeyboardButton("30 min", callback_data=f"snooze_do_{reminder_id}_30"),
        ],
        [
            InlineKeyboardButton(h1_label, callback_data=f"snooze_do_{reminder_id}_60"),
            InlineKeyboardButton(cancel_label, callback_data=f"snooze_cancel_{reminder_id}"),
        ],
    ])

    current_text = query.message.text if query.message else ""
    prompt_snooze = "\n\n⏰ *Snooze until when?*" if user_lang == "en" else "\n\n⏰ *Adiar para quando?*"
    await query.edit_message_text(
        text=f"{current_text}{prompt_snooze}",
        reply_markup=snooze_keyboard,
        parse_mode="Markdown",
    )


async def reminder_snooze_execute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    parts = query.data.split("_")
    reminder_id = int(parts[2])
    minutes = int(parts[3])

    user = update.effective_user
    user_lang = "pt"

    with get_db() as session:
        if user and isinstance(getattr(user, "id", None), int):
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                user_lang = getattr(db_user, "language", "pt") or "pt"

        original_reminder = ReminderRepository.get_by_id(session, reminder_id)
        if not original_reminder:
            await query.edit_message_text("⚠️ Lembrete não encontrado.")
            return

        from app.database.models import ReminderStatus
        if original_reminder.status == ReminderStatus.PENDING:
            ReminderRepository.mark_as_sent(session, original_reminder.id)

        new_scheduled_at = utc_now() + timedelta(minutes=minutes)
        ReminderRepository.create(
            session=session,
            event_id=original_reminder.event_id,
            scheduled_at=new_scheduled_at,
            minutes_before=minutes,
            user_id=original_reminder.user_id,
        )
        local_remind_time = to_local_tz(new_scheduled_at).strftime("%H:%M")

    current_text = query.message.text if query.message else ""
    for marker in ["⏰ *Adiar para quando?*", "⏰ *Snooze until when?*"]:
        if marker in current_text:
            current_text = current_text.split(marker)[0].strip()

    if user_lang == "en":
        result_text = f"{current_text}\n\n⏰ *Snoozed:* Next reminder scheduled for {local_remind_time}."
    else:
        result_text = f"{current_text}\n\n⏰ *Adiado:* Novo aviso agendado para às {local_remind_time}."

    await query.edit_message_text(text=result_text, reply_markup=None, parse_mode="Markdown")


async def reminder_snooze_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    reminder_id = int(query.data.replace("snooze_cancel_", ""))

    user = update.effective_user
    user_lang = "pt"
    if user and isinstance(getattr(user, "id", None), int):
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                user_lang = getattr(db_user, "language", "pt") or "pt"

    current_text = query.message.text if query.message else ""
    for marker in ["⏰ *Adiar para quando?*", "⏰ *Snooze until when?*"]:
        if marker in current_text:
            current_text = current_text.split(marker)[0].strip()

    original_keyboard = get_reminder_action_keyboard(reminder_id, lang=user_lang)
    await query.edit_message_text(text=current_text, reply_markup=original_keyboard, parse_mode="Markdown")
