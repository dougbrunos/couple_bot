import logging
from datetime import timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope
from app.database.repositories.reminder_repo import ReminderRepository
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.utils.date_utils import utc_now, to_local_tz, get_local_now
from app.utils.i18n import t

logger = logging.getLogger(__name__)


def get_reminder_action_keyboard(reminder_id: int, lang: str = "pt") -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton(t("btn_rem_ok", lang), callback_data=f"rem_ack_{reminder_id}"),
            InlineKeyboardButton(t("btn_rem_snooze", lang), callback_data=f"rem_snooze_{reminder_id}"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def check_and_send_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    now = utc_now()
    notifications = []

    with get_db() as session:
        pending_reminders = ReminderRepository.list_pending(session, current_time=now)
        if not pending_reminders:
            return

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
            time_str = local_event_time.strftime("%H:%M")

            user_1 = UserRepository.get_by_id(session, couple.user_1_id)
            user_2 = UserRepository.get_by_id(session, couple.user_2_id) if couple.user_2_id else None

            recipients_data = []
            if event.scope == EventScope.SHARED:
                u1_name = user_1.name if user_1 else "Partner"
                u2_name = user_2.name if user_2 else "Partner"
                for target in [user_1, user_2]:
                    if not target:
                        continue
                    lang = getattr(target, "language", "pt") or "pt"
                    if local_event_time.date() == local_now.date():
                        date_prefix = "Today" if lang == "en" else "Hoje"
                    elif local_event_time.date() == (local_now.date() + timedelta(days=1)):
                        date_prefix = "Tomorrow" if lang == "en" else "Amanhã"
                    else:
                        date_prefix = local_event_time.strftime("%d/%m")

                    header = "🔔 *COUPLE REMINDER*" if lang == "en" else "🔔 *LEMBRETE DO CASAL*"
                    at_word = "at" if lang == "en" else "às"
                    msg = (
                        f"{header}\n\n"
                        f"🍽️ *{event.title}*\n\n"
                        f"{date_prefix} {at_word} {time_str}.\n\n"
                        f"❤️ {u1_name} + {u2_name}"
                    )
                    recipients_data.append((target.telegram_id, msg, lang))
            else:
                target_user = UserRepository.get_by_id(session, rem.user_id) if rem.user_id else user_1
                if target_user:
                    lang = getattr(target_user, "language", "pt") or "pt"
                    if local_event_time.date() == local_now.date():
                        date_prefix = "Today" if lang == "en" else "Hoje"
                    elif local_event_time.date() == (local_now.date() + timedelta(days=1)):
                        date_prefix = "Tomorrow" if lang == "en" else "Amanhã"
                    else:
                        date_prefix = local_event_time.strftime("%d/%m")

                    header = "🔔 *REMINDER*" if lang == "en" else "🔔 *LEMBRETE*"
                    u_name = target_user.name or ("You" if lang == "en" else "Você")
                    at_word = "at" if lang == "en" else "às"
                    msg = (
                        f"{header}\n\n"
                        f"📌 *{event.title}*\n\n"
                        f"{date_prefix} {at_word} {time_str}.\n\n"
                        f"👤 {u_name}"
                    )
                    recipients_data.append((target_user.telegram_id, msg, lang))

            notifications.append({
                "reminder_id": rem.id,
                "recipients": recipients_data,
            })
            ReminderRepository.mark_as_sent(session, rem.id)

    for item in notifications:
        for chat_id, text, lang in item["recipients"]:
            reply_markup = get_reminder_action_keyboard(item["reminder_id"], lang=lang)
            try:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode="Markdown",
                )
            except Exception as e:
                logger.error(f"Error sending reminder {item['reminder_id']} to {chat_id}: {e}")
