import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from app.database.database import get_db
from app.database.models import EventScope
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.database.repositories.event_repo import EventRepository
from app.bot.keyboards.main_menu import get_main_menu_keyboard
from app.utils.date_utils import utc_now, to_local_tz

logger = logging.getLogger(__name__)


async def delete_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Apresenta a lista de eventos do casal com botões para escolher qual excluir."""
    user = update.effective_user
    if not user:
        return

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(session, user.id, user.first_name or "Usuário")

        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None

        if not is_paired or not couple:
            menu_kb = get_main_menu_keyboard(is_paired=False)
            text = "⚠️ Você precisa estar conectado(a) em um casal para gerenciar eventos."
            if update.callback_query:
                await update.callback_query.answer()
                await update.callback_query.edit_message_text(text, reply_markup=menu_kb)
            elif update.message:
                await update.message.reply_text(text, reply_markup=menu_kb)
            return

        couple_id = couple.id
        raw_events = EventRepository.list_upcoming(session, couple_id, from_time=utc_now(), limit=20)
        events_data = []
        for ev in raw_events:
            local_dt = to_local_tz(ev.start_at)
            events_data.append({
                "id": ev.id,
                "title": ev.title,
                "date_str": local_dt.strftime("%d/%m"),
                "time_str": local_dt.strftime("%H:%M"),
            })

    if not events_data:
        text = "🗑 *Excluir Eventos*\n\nVocê não possui eventos futuros cadastrados para excluir."
        back_kb = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Voltar ao menu", callback_data="menu_main")]])
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(text, reply_markup=back_kb, parse_mode="Markdown")
        elif update.message:
            await update.message.reply_text(text, reply_markup=back_kb, parse_mode="Markdown")
        return

    buttons = []
    for item in events_data:
        btn_text = f"🗑️ {item['title']} — {item['date_str']}"
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"del_sel_{item['id']}")])

    buttons.append([InlineKeyboardButton("❌ Cancelar", callback_data="menu_main")])
    keyboard = InlineKeyboardMarkup(buttons)

    text = "🗑 *Qual evento deseja excluir?*\n\nEscolha na lista abaixo:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def confirm_delete_prompt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Exibe tela de confirmação para exclusão de um evento específico."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    event_id = int(query.data.replace("del_sel_", ""))
    user = update.effective_user

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        couple = CoupleRepository.get_by_user_id(session, db_user.id) if db_user else None
        event = EventRepository.get_by_id(session, event_id)

        if not couple or not event or event.couple_id != couple.id:
            await query.edit_message_text(
                "⚠️ Evento não encontrado ou você não tem permissão para excluí-lo.",
                reply_markup=get_main_menu_keyboard(is_paired=bool(couple)),
            )
            return

        local_dt = to_local_tz(event.start_at)
        title = event.title
        date_str = local_dt.strftime("%d/%m")
        time_str = local_dt.strftime("%H:%M")

    confirm_keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Excluir", callback_data=f"del_confirm_{event_id}")],
        [InlineKeyboardButton("Cancelar", callback_data="menu_delete")],
    ])

    text = "⚠️ *Excluir este evento?*\n\n"
    text += f"🍽️ *{title}*\n"
    text += f"📆 {date_str} às {time_str}"

    await query.edit_message_text(text, reply_markup=confirm_keyboard, parse_mode="Markdown")


async def execute_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Executa a exclusão definitiva do evento."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()
    event_id = int(query.data.replace("del_confirm_", ""))
    user = update.effective_user

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        couple = CoupleRepository.get_by_user_id(session, db_user.id) if db_user else None
        event = EventRepository.get_by_id(session, event_id)

        if not couple or not event or event.couple_id != couple.id:
            await query.edit_message_text(
                "⚠️ Evento não encontrado ou já excluído.",
                reply_markup=get_main_menu_keyboard(is_paired=bool(couple)),
            )
            return

        title = event.title
        is_shared = (event.scope == EventScope.SHARED)
        partner = CoupleRepository.get_partner(session, db_user.id)
        partner_tg_id = partner.telegram_id if partner else None

        EventRepository.delete(session, event_id)

    menu_kb = get_main_menu_keyboard(is_paired=True)
    await query.edit_message_text("✅ Evento excluído.", reply_markup=menu_kb)

    # Notifica parceiro se for compartilhado
    if is_shared and partner_tg_id:
        try:
            await context.bot.send_message(
                chat_id=partner_tg_id,
                text=f"🗑️ O evento compartilhado *'{title}'* foi excluído por *{user.first_name}*.",
                reply_markup=menu_kb,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.warning(f"Erro ao notificar parceiro sobre exclusão: {e}")
