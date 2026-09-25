from telegram import Update
from telegram.ext import ContextTypes
from app.database.database import get_db
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.bot.keyboards.main_menu import get_main_menu_keyboard


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para os comandos /ajuda e /help: exibe instruções e comandos do bot."""
    user = update.effective_user
    if not user:
        return

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        is_paired = False
        has_pending_invite = False
        if db_user:
            couple = CoupleRepository.get_by_user_id(session, db_user.id)
            is_paired = couple is not None and couple.user_2_id is not None
            has_pending_invite = couple is not None and couple.user_2_id is None

    text = "📖 *Guia de Uso do Assistente de Casal*\n\n"
    text += "Aqui estão os comandos principais que você pode usar:\n\n"
    text += "• /start ou /menu — Abre o menu principal de navegação.\n"
    text += "• /ajuda — Mostra esta mensagem de ajuda.\n"

    if is_paired:
        text += "• /add — Cria um novo evento (pessoal ou compartilhado).\n"
        text += "• /hoje — Consulta os compromissos do dia.\n"
        text += "• /semana — Consulta os compromissos dos próximos 7 dias.\n"
        text += "• /eventos — Lista os próximos eventos cadastrados.\n"
        text += "• /delete — Permite excluir um compromisso existente.\n"
    else:
        text += "\n⚠️ *Atenção:* Vocês ainda não estão vinculados como casal. Use o menu abaixo para criar ou entrar em um casal."

    keyboard = get_main_menu_keyboard(is_paired=is_paired, has_pending_invite=has_pending_invite)

    if update.message:
        await update.message.reply_text(text, reply_markup=keyboard, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
