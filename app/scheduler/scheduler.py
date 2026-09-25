import logging
from typing import List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope, Reminder
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.utils.date_utils import utc_now, to_local_tz, get_local_now

logger = logging.getLogger(__name__)


def get_reminder_action_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    """Retorna os botões de ação para a notificação de lembrete: OK e Adiar."""
    keyboard = [
        [
            InlineKeyboardButton("✓ OK", callback_data=f"rem_ack_{reminder_id}"),
            InlineKeyboardButton("⏰ Adiar", callback_data=f"rem_snooze_{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def check_and_send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job periódico executado pelo JobQueue para processar e disparar lembretes pendentes."""
    now = utc_now()
    notifications = []

    with get_db() as session:
        pending_reminders = ReminderRepository.list_pending(session, current_time=now)
        if not pending_reminders:
            return

        logger.info(f"Processando {len(pending_reminders)} lembrete(s) pendente(s)...")

        for rem in pending_reminders:
            event = rem.event
            if not event:
                ReminderRepository.mark_as_cancelled(session, rem.id)
                continue

            couple = CoupleRepository.get_by_id(session, event.couple_id)
            if not couple:
                ReminderRepository.mark_as_cancelled(session, rem.id)
                continue

            local_event_time = to_local_tz(event.start_at)
            local_now = get_local_now()

            if local_event_time.date() == local_now.date():
                date_prefix = "Hoje"
            elif local_event_time.date() == (local_now.date() + local_now.resolution):
                date_prefix = "Amanhã"
            else:
                date_prefix = local_event_time.strftime("%d/%m")

            time_str = local_event_time.strftime("%H:%M")

            user_1 = UserRepository.get_by_id(session, couple.user_1_id)
            user_2 = UserRepository.get_by_id(session, couple.user_2_id) if couple.user_2_id else None

            # Determina destinatários e texto da mensagem
            recipients = []
            if event.scope == EventScope.SHARED:
                u1_name = user_1.name if user_1 else "Parceiro"
                u2_name = user_2.name if user_2 else "Parceira"
                text = (
                    "🔔 *LEMBRETE DO CASAL*\n\n"
                    f"🍽️ *{event.title}*\n\n"
                    f"{date_prefix} às {time_str}.\n\n"
                    f"❤️ {u1_name} + {u2_name}"
                )
                if user_1:
                    recipients.append(user_1.telegram_id)
                if user_2:
                    recipients.append(user_2.telegram_id)
            else:
                target_user = UserRepository.get_by_id(session, rem.user_id) if rem.user_id else user_1
                u_name = target_user.name if target_user else "Você"
                text = (
                    "🔔 *LEMBRETE*\n\n"
                    f"📌 *{event.title}*\n\n"
                    f"{date_prefix} às {time_str}.\n\n"
                    f"👤 {u_name}"
                )
                if target_user:
                    recipients.append(target_user.telegram_id)

            notifications.append({
                "reminder_id": rem.id,
                "recipients": recipients,
                "text": text,
            })

            ReminderRepository.mark_as_sent(session, rem.id)

    # Dispara mensagens fora da sessão do banco para evitar bloqueios
    for item in notifications:
        reply_markup = get_reminder_action_keyboard(item["reminder_id"])
        for chat_id in item["recipients"]:
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=item["text"],
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Erro ao enviar lembrete {item['reminder_id']} para chat {chat_id}: {e}")
