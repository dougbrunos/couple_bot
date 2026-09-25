import logging
from datetime import timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.database.repositories.event_repo import EventRepository
from app.services.event_service import EventService, EventView
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.utils.date_utils import get_local_now, utc_now, to_local_tz

logger = logging.getLogger(__name__)

WEEKDAY_NAMES = ["SEG", "TER", "QUA", "QUI", "SEX", "SÁB", "DOM"]


async def today_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para consultar compromissos de hoje (/hoje ou botão [📅 Hoje])."""
    user = update.effective_user
    if not user:
        return

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False)
            text = "⚠️ Você precisa estar conectado(a) em um casal para consultar compromissos."
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
    menu_kb = get_main_menu_keyboard(is_paired=True)

    if not events_list:
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

    text = f"📅 *HOJE — {formatted_date}*\n\n"

    if user_items:
        text += f"👤 *{user_name.upper()}*\n"
        text += "\n".join(user_items) + "\n\n"

    if partner_items:
        text += f"👩 *{partner_name.upper()}*\n"
        text += "\n".join(partner_items) + "\n\n"

    if shared_items:
        text += "❤️ *JUNTOS*\n"
        text += "\n".join(shared_items) + "\n\n"

    total = len(events_list)
    s = "s" if total > 1 else ""
    text += f"Você tem {total} compromisso{s} hoje."

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=menu_kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=menu_kb, parse_mode="Markdown")


async def week_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para consultar os compromissos dos próximos 7 dias (/semana ou botão [🗓 Semana])."""
    user = update.effective_user
    if not user:
        return

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False)
            text = "⚠️ Você precisa estar conectado(a) em um casal para consultar a semana."
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

    menu_kb = get_main_menu_keyboard(is_paired=True)
    text = "🗓 *PRÓXIMOS 7 DIAS*\n\n"

    for day_date, events in week_events:
        weekday_label = WEEKDAY_NAMES[day_date.weekday()]
        day_str = day_date.strftime("%d/%m")
        header = f"*{weekday_label} {day_str}*"

        if not events:
            text += f"{header}\nNenhum evento.\n\n"
        else:
            lines = []
            for ev in events:
                time_str = ev.local_time.strftime("%H:%M")
                if ev.scope == EventScope.SHARED:
                    part_str = "❤️ Nós dois"
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
    """Handler para listar próximos eventos cadastrados (/eventos ou botão [📋 Eventos])."""
    user = update.effective_user
    if not user:
        return

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False)
            text = "⚠️ Você precisa estar conectado(a) em um casal para listar eventos."
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

        # Carrega eventos futuros e extrai dados primitivos para evitar DetachedInstanceError
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
        [InlineKeyboardButton("➕ Novo evento", callback_data="menu_add_event")],
        [InlineKeyboardButton("🗑 Excluir evento", callback_data="menu_delete")],
        [InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu_main")],
    ])

    if not event_dto_list:
        text = "📋 *PRÓXIMOS EVENTOS*\n\nNenhum evento futuro cadastrado."
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
        elif update.message:
            await update.message.reply_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
        return

    text = "📋 *PRÓXIMOS EVENTOS*\n\n"
    for idx, item in enumerate(event_dto_list, 1):
        if item["scope"] == EventScope.SHARED:
            part_str = "❤️ Nós dois"
        elif item["owner_id"] == user_id:
            part_str = f"👤 {user_name}"
        else:
            part_str = f"👩 {partner_name}"

        text += f"{idx}. *{item['title']}*\n"
        text += f"{item['date_str']} — {item['time_str']}\n"
        text += f"{part_str}\n\n"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=nav_keyboard, parse_mode="Markdown")
