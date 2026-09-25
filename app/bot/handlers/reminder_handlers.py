import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.repositories.user_repo import UserRepository
from app.utils.date_utils import utc_now, to_local_tz
from app.scheduler.scheduler import get_reminder_action_keyboard

logger = logging.getLogger(__name__)


async def reminder_ack_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Confirma o recebimento do lembrete e remove os botões inline."""
    query = update.callback_query
    if not query:
        return

    await query.answer("Lembrete confirmado!")
    current_text = query.message.text if query.message else ""
    updated_text = f"{current_text}\n\n✓ *Confirmado*"
    await query.edit_message_text(text=updated_text, reply_markup=None, parse_mode="Markdown")


async def reminder_snooze_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Apresenta as opções de tempo para adiar o lembrete."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    reminder_id = int(query.data.replace("rem_snooze_", ""))

    snooze_keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("10 min", callback_data=f"snooze_do_{reminder_id}_10"),
            InlineKeyboardButton("30 min", callback_data=f"snooze_do_{reminder_id}_30"),
        ],
        [
            InlineKeyboardButton("1 hora", callback_data=f"snooze_do_{reminder_id}_60"),
            InlineKeyboardButton("Cancelar", callback_data=f"snooze_cancel_{reminder_id}"),
        ],
    ])

    current_text = query.message.text if query.message else ""
    await query.edit_message_text(
        text=f"{current_text}\n\n⏰ *Adiar para quando?*",
        reply_markup=snooze_keyboard,
        parse_mode="Markdown",
    )


async def reminder_snooze_execute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cria um novo lembrete temporário adiado no banco de dados."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    parts = query.data.split("_")
    reminder_id = int(parts[2])
    minutes = int(parts[3])

    with get_db() as session:
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
    # Remove a pergunta "Adiar para quando?" se presente
    base_text = current_text.split("⏰ *Adiar para quando?*")[0].strip()

    result_text = f"{base_text}\n\n⏰ *Adiado:* Novo aviso agendado para às {local_remind_time}."
    await query.edit_message_text(text=result_text, reply_markup=None, parse_mode="Markdown")


async def reminder_snooze_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancela o adiamento e restaura os botões originais."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    reminder_id = int(query.data.replace("snooze_cancel_", ""))

    current_text = query.message.text if query.message else ""
    base_text = current_text.split("⏰ *Adiar para quando?*")[0].strip()

    original_keyboard = get_reminder_action_keyboard(reminder_id)
    await query.edit_message_text(text=base_text, reply_markup=original_keyboard, parse_mode="Markdown")
