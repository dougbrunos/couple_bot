from telegram import Update
from telegram.ext import ContextTypes
from app.database.database import get_db
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.bot.keyboards.main_menu import get_main_menu_keyboard


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    user_lang = "pt"
    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        is_paired = False
        has_pending_invite = False
        if db_user:
            user_lang = getattr(db_user, "language", "pt") or "pt"
            couple = CoupleRepository.get_by_user_id(session, db_user.id)
            is_paired = couple is not None and couple.user_2_id is not None
            has_pending_invite = couple is not None and couple.user_2_id is None

    text = "📖 *Guia de Uso e Comandos | Commands & User Guide*\n\n"
    text += "Você pode usar comandos em Português ou Inglês:\n"
    text += "_You can use commands in either Portuguese or English:_\n\n"
    text += "• /start | /menu — Menu principal / Main menu\n"
    text += "• /ajuda | /help — Guia de ajuda / Help guide\n"

    if is_paired:
        text += "• /add | /novo — Criar evento / New event\n"
        text += "• /hoje | /today — Compromissos de hoje / Today's events\n"
        text += "• /semana | /week — Próximos 7 dias / Next 7 days\n"
        text += "• /eventos | /events — Lista de eventos / All events\n"
        text += "• /delete | /excluir — Excluir evento / Delete event\n"
        text += "• /cancelar | /cancel — Cancelar fluxo / Cancel action\n"
        text += "• /language | /idioma — Mudar idioma / Change language\n"
    else:
        text += "• /criar\\_casal | /create\\_couple — Gerar código / Create couple invite\n"
        text += "• /entrar\\_casal | /join\\_couple — Entrar com código / Join couple\n"
        text += "• /language | /idioma — Mudar idioma / Change language\n"
        text += "\n⚠️ *Atenção:* Vocês ainda não estão vinculados como casal. Use o menu abaixo para conectar-se ao seu parceiro."

    keyboard = get_main_menu_keyboard(
        is_paired=is_paired, has_pending_invite=has_pending_invite, lang=user_lang
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
