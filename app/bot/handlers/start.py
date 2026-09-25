import logging
from telegram import Update
from telegram.ext import ContextTypes
from app.database.database import get_db
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.bot.keyboards.main_menu import get_main_menu_keyboard

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler para o comando /start: cadastra/atualiza usuário e envia mensagem inicial."""
    user = update.effective_user
    if not user:
        return

    telegram_id = user.id
    name = user.first_name or "Parceiro"

    with get_db() as session:
        db_user = UserRepository.create_or_update(session, telegram_id=telegram_id, name=name)
        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        has_pending_invite = couple is not None and couple.user_2_id is None

    greeting = f"👋 Olá, {name}!\n\n"
    greeting += "Sou o assistente de organização de vocês.\n\n"
    greeting += "Posso ajudar a organizar:\n"
    greeting += "📅 compromissos\n"
    greeting += "⏰ lembretes\n"
    greeting += "❤️ eventos compartilhados\n\n"

    if is_paired:
        greeting += "Escolha uma opção no menu abaixo:"
    elif has_pending_invite:
        greeting += "Você tem um convite de casal aberto! Compartilhe o código com sua parceira para se conectarem."
    else:
        greeting += "Para começarem, vinculem o casal usando as opções abaixo:"

    keyboard = get_main_menu_keyboard(is_paired=is_paired, has_pending_invite=has_pending_invite)

    if update.message:
        await update.message.reply_text(greeting, reply_markup=keyboard)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(greeting, reply_markup=keyboard)
