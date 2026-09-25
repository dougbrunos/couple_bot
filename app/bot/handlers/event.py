import logging
from datetime import date, time
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from app.database.database import get_db
from app.database.models import EventScope, RecurrenceType
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.services.event_service import EventService
from app.bot.states.event_states import (
    EVENT_TITLE,
    EVENT_DATE,
    EVENT_TIME,
    EVENT_PARTICIPANT,
    EVENT_RECURRENCE,
    EVENT_REMINDER,
    EVENT_CONFIRM,
)
from app.bot.keyboards.event_keyboards import (
    get_cancel_event_keyboard,
    get_participant_keyboard,
    get_recurrence_keyboard,
    get_reminder_keyboard,
    get_confirm_event_keyboard,
)
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.utils.date_utils import (
    parse_date_input,
    parse_time_input,
    get_local_now,
    to_local_tz,
)
from app.utils.i18n import t

logger = logging.getLogger(__name__)


async def start_add_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    if not user:
        return ConversationHandler.END

    user_lang = "pt"
    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        user_lang = getattr(db_user, "language", "pt") or "pt"
        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        partner = CoupleRepository.get_partner(session, db_user.id) if couple else None

        couple_id = couple.id if couple else None
        db_user_id = db_user.id
        partner_id = partner.id if partner else None
        partner_name = partner.name if partner else "Partner"

    if not is_paired or not couple_id:
        text = (
            "⚠️ Para criar e organizar eventos, você precisa estar conectado(a) em um casal!\n\n"
            "Use as opções do menu para criar ou entrar em um casal."
            if user_lang == "pt"
            else "⚠️ To create and organize events, you need to be connected as a couple!\n\n"
            "Use the menu options to create or join a couple."
        )
        menu_kb = get_main_menu_keyboard(is_paired=False, lang=user_lang)
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=menu_kb)
        elif update.message:
            await update.message.reply_text(text, reply_markup=menu_kb)
        return ConversationHandler.END

    context.user_data["event_draft"] = {
        "user_name": user.first_name or "Eu",
        "partner_name": partner_name,
        "couple_id": couple_id,
        "user_id": db_user_id,
        "partner_id": partner_id,
        "lang": user_lang,
    }

    text = t("event_add_title_prompt", user_lang)
    cancel_kb = get_cancel_event_keyboard(lang=user_lang)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=cancel_kb, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=cancel_kb, parse_mode="Markdown")

    return EVENT_TITLE


async def process_event_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return EVENT_TITLE

    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")
    title = update.message.text.strip()

    if len(title) < 2:
        short_err = (
            "⚠️ Title is too short. Please send a more descriptive name:"
            if lang == "en"
            else "⚠️ O título é muito curto. Por favor, envie um nome mais descritivo para o evento:"
        )
        await update.message.reply_text(short_err, reply_markup=get_cancel_event_keyboard(lang=lang))
        return EVENT_TITLE

    draft["title"] = title
    context.user_data["event_draft"] = draft

    example_fmt = "`26/09/2026`"
    text = (
        f"📆 *What is the date for \"{title}\"?*\n\nExample: {example_fmt}"
        if lang == "en"
        else f"📆 *Qual a data para \"{title}\"?*\n\nExemplo: {example_fmt}"
    )
    await update.message.reply_text(text, reply_markup=get_cancel_event_keyboard(lang=lang), parse_mode="Markdown")
    return EVENT_DATE


async def process_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return EVENT_DATE

    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")
    date_str = update.message.text.strip()
    parsed_date, error = parse_date_input(date_str)

    if error or not parsed_date:
        await update.message.reply_text(
            t("event_invalid_date", lang, example="26/09/2026"),
            reply_markup=get_cancel_event_keyboard(lang=lang),
            parse_mode="Markdown",
        )
        return EVENT_DATE

    draft["date"] = parsed_date
    context.user_data["event_draft"] = draft

    formatted_date = parsed_date.strftime("%d/%m/%Y")
    text = (
        f"🕐 *What time for {formatted_date}?*\n\nExample: `20:00`"
        if lang == "en"
        else f"🕐 *Qual o horário para {formatted_date}?*\n\nExemplo: `20:00`"
    )
    await update.message.reply_text(text, reply_markup=get_cancel_event_keyboard(lang=lang), parse_mode="Markdown")
    return EVENT_TIME


async def process_event_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not update.message or not update.message.text:
        return EVENT_TIME

    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")
    time_str = update.message.text.strip()
    parsed_time, error = parse_time_input(time_str)

    if error or not parsed_time:
        await update.message.reply_text(
            t("event_invalid_time", lang),
            reply_markup=get_cancel_event_keyboard(lang=lang),
            parse_mode="Markdown",
        )
        return EVENT_TIME

    event_date: date = draft.get("date")
    local_now = get_local_now()
    if event_date == local_now.date() and parsed_time < local_now.time():
        past_err = (
            "⚠️ That time has already passed today! Please enter a future time (e.g. `20:00`):"
            if lang == "en"
            else "⚠️ Esse horário já passou hoje! Por favor, informe um horário futuro (ex: `20:00`):"
        )
        await update.message.reply_text(past_err, reply_markup=get_cancel_event_keyboard(lang=lang), parse_mode="Markdown")
        return EVENT_TIME

    draft["time"] = parsed_time
    context.user_data["event_draft"] = draft

    user_name = draft.get("user_name", "Eu")
    partner_name = draft.get("partner_name", "Ela")
    part_kb = get_participant_keyboard(user_name=user_name, partner_name=partner_name, lang=lang)

    text = t("event_add_scope_prompt", lang)
    await update.message.reply_text(text, reply_markup=part_kb, parse_mode="Markdown")
    return EVENT_PARTICIPANT


async def process_event_participant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return EVENT_PARTICIPANT

    await query.answer()
    data = query.data
    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")

    if data == "scope_personal":
        draft["scope"] = EventScope.PERSONAL
        draft["owner_id"] = draft.get("user_id")
    elif data == "scope_partner":
        draft["scope"] = EventScope.PARTNER
        draft["owner_id"] = draft.get("partner_id")
    else:
        draft["scope"] = EventScope.SHARED
        draft["owner_id"] = None

    context.user_data["event_draft"] = draft
    text = t("event_add_recurrence_prompt", lang)
    await query.edit_message_text(text, reply_markup=get_recurrence_keyboard(lang=lang), parse_mode="Markdown")
    return EVENT_RECURRENCE


async def process_event_recurrence(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return EVENT_RECURRENCE

    await query.answer()
    data = query.data
    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")

    mapping = {
        "recur_none": RecurrenceType.NONE,
        "recur_daily": RecurrenceType.DAILY,
        "recur_weekly": RecurrenceType.WEEKLY,
        "recur_monthly": RecurrenceType.MONTHLY,
        "recur_yearly": RecurrenceType.YEARLY,
    }
    draft["recurrence_type"] = mapping.get(data, RecurrenceType.NONE)
    context.user_data["event_draft"] = draft

    text = t("event_add_reminder_prompt", lang)
    await query.edit_message_text(text, reply_markup=get_reminder_keyboard(lang=lang), parse_mode="Markdown")
    return EVENT_REMINDER


async def process_event_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return EVENT_REMINDER

    await query.answer()
    data = query.data
    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")

    reminder_map = {
        "remind_none": 0,
        "remind_10": 10,
        "remind_30": 30,
        "remind_60": 60,
        "remind_1440": 1440,
    }
    reminder_minutes = reminder_map.get(data, 0)
    draft["reminder_minutes"] = reminder_minutes
    context.user_data["event_draft"] = draft

    scope_labels = {
        EventScope.PERSONAL: f"👤 {draft.get('user_name', 'Eu')}",
        EventScope.PARTNER: f"👩 {draft.get('partner_name', 'Partner')}",
        EventScope.SHARED: f"❤️ {draft.get('user_name', 'Eu')} + {draft.get('partner_name', 'Partner')}",
    }
    recurrence_labels = {
        RecurrenceType.NONE: t("recur_none", lang),
        RecurrenceType.DAILY: t("recur_daily", lang),
        RecurrenceType.WEEKLY: t("recur_weekly", lang),
        RecurrenceType.MONTHLY: t("recur_monthly", lang),
        RecurrenceType.YEARLY: t("recur_yearly", lang),
    }
    reminder_labels = {
        0: t("remind_none", lang),
        10: t("remind_10m", lang),
        30: t("remind_30m", lang),
        60: t("remind_1h", lang),
        1440: t("remind_1d", lang),
    }

    event_date: date = draft.get("date")
    event_time: time = draft.get("time")
    formatted_date = event_date.strftime("%d/%m/%Y")
    formatted_time = event_time.strftime("%H:%M")

    summary_header = "📋 *EVENT CONFIRMATION*\n\n" if lang == "en" else "📋 *CONFIRMAR EVENTO*\n\n"
    summary = (
        f"{summary_header}"
        f"📌 *{draft.get('title')}*\n"
        f"📆 {formatted_date}\n"
        f"🕐 {formatted_time}\n"
        f"👥 {scope_labels.get(draft.get('scope'))}\n"
        f"🔁 {recurrence_labels.get(draft.get('recurrence_type'))}\n"
        f"🔔 {reminder_labels.get(reminder_minutes)}\n"
    )

    await query.edit_message_text(summary, reply_markup=get_confirm_event_keyboard(lang=lang), parse_mode="Markdown")
    return EVENT_CONFIRM


async def process_event_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if not query:
        return EVENT_CONFIRM

    await query.answer()
    draft = context.user_data.get("event_draft", {})
    lang = draft.get("lang", "pt")

    if not draft or "title" not in draft:
        err = "⚠️ Event data not found. Type /add to try again." if lang == "en" else "⚠️ Dados do evento não encontrados. Digite /add para tentar novamente."
        await query.edit_message_text(err)
        return ConversationHandler.END

    with get_db() as session:
        event, reminder = EventService.create_event(
            session=session,
            couple_id=draft["couple_id"],
            created_by=draft["user_id"],
            title=draft["title"],
            event_date=draft["date"],
            event_time=draft["time"],
            scope=draft["scope"],
            owner_id=draft.get("owner_id"),
            recurrence_type=draft["recurrence_type"],
            reminder_minutes=draft.get("reminder_minutes"),
        )
        reminder_time = reminder.scheduled_at if reminder else None
        partner = UserRepository.get_by_id(session, draft["partner_id"]) if draft.get("partner_id") else None
        partner_tg_id = partner.telegram_id if partner else None
        partner_lang = getattr(partner, "language", "pt") if partner else "pt"

    if lang == "en":
        success_text = "✅ *Event created!*\n\n"
        if reminder_time:
            local_remind = to_local_tz(reminder_time)
            success_text += f"Reminder set for {local_remind.strftime('%H:%M')} on {local_remind.strftime('%d/%m')}."
        else:
            success_text += "Appointment added to schedule."
    else:
        success_text = "✅ *Evento criado!*\n\n"
        if reminder_time:
            local_remind = to_local_tz(reminder_time)
            success_text += f"Vou lembrar às {local_remind.strftime('%H:%M')} de {local_remind.strftime('%d/%m')}."
        else:
            success_text += "Compromisso adicionado à agenda."

    menu_kb = get_main_menu_keyboard(is_paired=True, lang=lang)
    await query.edit_message_text(success_text, reply_markup=menu_kb, parse_mode="Markdown")

    if partner_tg_id and draft["scope"] in (EventScope.SHARED, EventScope.PARTNER):
        if partner_lang == "en":
            partner_notice = (
                f"📅 *New event added!*\n\n"
                f"*{draft['title']}*\n"
                f"📆 {draft['date'].strftime('%d/%m/%Y')} at {draft['time'].strftime('%H:%M')}\n"
                f"Added by: *{draft['user_name']}*"
            )
        else:
            partner_notice = (
                f"📅 *Novo evento adicionado!*\n\n"
                f"*{draft['title']}*\n"
                f"📆 {draft['date'].strftime('%d/%m/%Y')} às {draft['time'].strftime('%H:%M')}\n"
                f"Adicionado por: *{draft['user_name']}*"
            )
        try:
            await context.bot.send_message(
                chat_id=partner_tg_id,
                text=partner_notice,
                reply_markup=get_main_menu_keyboard(is_paired=True, lang=partner_lang),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Could not notify partner about new event: {e}")

    context.user_data.pop("event_draft", None)
    return ConversationHandler.END


async def cancel_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    draft = context.user_data.pop("event_draft", {})
    lang = draft.get("lang", "pt")
    user = update.effective_user
    is_paired = False
    if user:
        with get_db() as session:
            db_user = UserRepository.get_by_telegram_id(session, user.id)
            if db_user:
                lang = getattr(db_user, "language", lang) or lang
                couple = CoupleRepository.get_by_user_id(session, db_user.id)
                is_paired = couple is not None and couple.user_2_id is not None

    menu_kb = get_main_menu_keyboard(is_paired=is_paired, lang=lang)
    text = t("event_cancelled", lang)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=menu_kb)
    elif update.message:
        await update.message.reply_text(text, reply_markup=menu_kb)

    return ConversationHandler.END


def get_add_event_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_event, pattern="^menu_add_event$"),
            CommandHandler(["add", "adicionar", "novo", "criar", "new", "create"], start_add_event),
        ],
        states={
            EVENT_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_event_title),
            ],
            EVENT_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_event_date),
            ],
            EVENT_TIME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_event_time),
            ],
            EVENT_PARTICIPANT: [
                CallbackQueryHandler(process_event_participant, pattern="^scope_(personal|partner|shared)$"),
            ],
            EVENT_RECURRENCE: [
                CallbackQueryHandler(process_event_recurrence, pattern="^recur_(none|daily|weekly|monthly|yearly)$"),
            ],
            EVENT_REMINDER: [
                CallbackQueryHandler(process_event_reminder, pattern="^remind_(none|10|30|60|1440)$"),
            ],
            EVENT_CONFIRM: [
                CallbackQueryHandler(process_event_confirm, pattern="^confirm_event_save$"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_event, pattern="^cancel_event$"),
            CommandHandler(["cancelar", "cancel"], cancel_event),
        ],
        per_message=False,
    )
