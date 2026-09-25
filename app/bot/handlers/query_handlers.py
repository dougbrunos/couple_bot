import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.database.repositories.event_repo import EventRepository
from app.services.event_service import EventService
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.utils.date_utils import get_local_now, utc_now, to_local_tz
from app.utils.i18n import t

logger = logging.getLogger(__name__)

WEEKDAYS_PT = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]
WEEKDAYS_EN = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    user_lang = "pt"
    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        user_lang = getattr(db_user, "language", "pt") or "pt"
        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False, lang=user_lang)
            text = t("status_unpaired", user_lang)
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text, reply_markup=menu_kb)
            elif update.message:
                await update.message.reply_text(text, reply_markup=menu_kb)
            return

        couple_id = couple.id
        user_id = db_user.id
        user_name = db_user.name
        partner_name = partner.name if partner else "Parceiro(a)"

        today = get_local_now().date()
        events_list = EventService.get_events_for_date(session, couple_id, today)

    formatted_date = today.strftime("%d/%m")
    menu_kb = get_main_menu_keyboard(is_paired=True, lang=user_lang)

    if not events_list:
        if user_lang == "en":
            text = f"📅 *TODAY — {formatted_date}*\n\nNo appointments scheduled.\n\nFree day. 👍"
        else:
            text = f"📅 *HOJE — {formatted_date}*\n\nNenhum compromisso registrado.\n\nDia livre. 👍"

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=menu_kb, parse_mode="Markdown")
        elif update.message:
            await update.message.reply_text(text, reply_markup=menu_kb, parse_mode="Markdown")
        return

    user_items = []
    partner_items = []
    shared_items = []

    for ev in events_list:
        time_str = ev.local_time.strftime("%H:%M")
        line = f"{time_str} — {ev.title}"
        if ev.scope == EventScope.SHARED:
            shared_items.append(line)
        elif ev.owner_id == user_id:
            user_items.append(line)
        else:
            partner_items.append(line)

    today_header = f"📅 *TODAY — {formatted_date}*\n\n" if user_lang == "en" else f"📅 *HOJE — {formatted_date}*\n\n"
    text = today_header

    if user_items:
        text += f"👤 *{user_name.upper()}*\n" + "\n".join(user_items) + "\n\n"

    if partner_items:
        text += f"👩 *{partner_name.upper()}*\n" + "\n".join(partner_items) + "\n\n"

    if shared_items:
        together_label = "❤️ *TOGETHER*" if user_lang == "en" else "❤️ *JUNTOS*"
        text += f"{together_label}\n" + "\n".join(shared_items) + "\n\n"

    total = len(events_list)
    if user_lang == "en":
        s = "s" if total > 1 else ""
        text += f"You have {total} appointment{s} today."
    else:
        s = "s" if total > 1 else ""
        text += f"Você tem {total} compromisso{s} hoje."

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=menu_kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=menu_kb, parse_mode="Markdown")


async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    user_lang = "pt"
    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        user_lang = getattr(db_user, "language", "pt") or "pt"
        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False, lang=user_lang)
            text = t("status_unpaired", user_lang)
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text, reply_markup=menu_kb)
            elif update.message:
                await update.message.reply_text(text, reply_markup=menu_kb)
            return

        couple_id = couple.id
        user_id = db_user.id
        user_name = db_user.name
        partner_name = partner.name if partner else "Parceira"

        today = get_local_now().date()
        week_events = []
        for i in range(7):
            day_date = today + timedelta(days=i)
            day_events = EventService.get_events_for_date(session, couple_id, day_date)
            week_events.append((day_date, day_events))

    menu_kb = get_main_menu_keyboard(is_paired=True, lang=user_lang)
    weekdays = WEEKDAYS_EN if user_lang == "en" else WEEKDAYS_PT
    header_title = "🗓 *NEXT 7 DAYS*\n\n" if user_lang == "en" else "🗓 *PRÓXIMOS 7 DIAS*\n\n"
    text = header_title

    no_event_text = "No events.\n\n" if user_lang == "en" else "Nenhum evento.\n\n"
    both_label = "❤️ Both" if user_lang == "en" else "❤️ Nós dois"

    for day_date, events in week_events:
        weekday_label = weekdays[day_date.weekday()]
        day_str = day_date.strftime("%d/%m")
        header = f"*{weekday_label} {day_str}*"

        if not events:
            text += f"{header}\n{no_event_text}"
        else:
            lines = []
            for ev in events:
                time_str = ev.local_time.strftime("%H:%M")
                if ev.scope == EventScope.SHARED:
                    part_str = both_label
                elif ev.owner_id == user_id:
                    part_str = f"👤 {user_name}"
                else:
                    part_str = f"👩 {partner_name}"
                lines.append(f"{time_str} — {ev.title} — {part_str}")
            text += f"{header}\n" + "\n".join(lines) + "\n\n"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=menu_kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=menu_kb, parse_mode="Markdown")


async def events_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    user_lang = "pt"
    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        user_lang = getattr(db_user, "language", "pt") or "pt"
        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False, lang=user_lang)
            text = t("status_unpaired", user_lang)
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text, reply_markup=menu_kb)
            elif update.message:
                await update.message.reply_text(text, reply_markup=menu_kb)
            return

        couple_id = couple.id
        user_id = db_user.id
        user_name = db_user.name
        partner_name = partner.name if partner else "Parceira"

        raw_events = EventRepository.list_upcoming(session, couple_id, from_time=utc_now(), limit=15)
        event_dto_list = []
        for ev in raw_events:
            local_dt = to_local_tz(ev.start_at)
            event_dto_list.append({
                "id": ev.id,
                "title": ev.title,
                "date_str": local_dt.strftime("%d/%m"),
                "time_str": local_dt.strftime("%H:%M"),
                "scope": ev.scope,
                "owner_id": ev.owner_id,
            })

    nav_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(t("btn_add_event", user_lang), callback_data="menu_add_event")],
        [InlineKeyboardButton(t("btn_delete", user_lang), callback_data="menu_delete")],
        [InlineKeyboardButton(t("btn_back_menu", user_lang), callback_data="menu_main")],
    ])

    title_label = "📋 *UPCOMING APPOINTMENTS*\n\n" if user_lang == "en" else "📋 *PRÓXIMOS EVENTOS*\n\n"
    both_label = "❤️ Both" if user_lang == "en" else "❤️ Nós dois"

    if not event_dto_list:
        empty_text = "No upcoming events scheduled." if user_lang == "en" else "Nenhum evento futuro cadastrado."
        text = f"{title_label}{empty_text}"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
        elif update.message:
            await update.message.reply_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
        return

    text = title_label
    for idx, item in enumerate(event_dto_list, 1):
        if item["scope"] == EventScope.SHARED:
            part_str = both_label
        elif item["owner_id"] == user_id:
            part_str = f"👤 {user_name}"
        else:
            part_str = f"👩 {partner_name}"

        text += f"{idx}. *{item['title']}*\n{item['date_str']} — {item['time_str']}\n{part_str}\n\n"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
