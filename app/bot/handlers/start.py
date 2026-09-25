from telegram import Update
from telegram.ext import ContextTypes
from app.database.database import get_db
from app.database.repositories.user_repo import UserRepository
from app.database.repositories.couple_repo import CoupleRepository
from app.bot.keyboards.main_menu import (
    get_main_menu_keyboard,
    get_language_selection_keyboard,
)
from app.utils.i18n import get_user_language


async def language_prompt_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    text = "🌐 **Por favor, selecione seu idioma / Please choose your language:**"
    keyboard = get_language_selection_keyboard()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )
    elif update.message:
        await update.message.reply_text(
            text, reply_markup=keyboard, parse_mode="Markdown"
        )


async def set_language_callback_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    lang = "en" if query.data == "set_lang_en" else "pt"
    user = update.effective_user
    if user:
        with get_db() as session:
            UserRepository.set_language(session, user.id, lang)
        if hasattr(context, "user_data") and isinstance(context.user_data, dict):
            context.user_data["lang"] = lang
            context.user_data["lang_selected"] = True

    await send_main_menu(update, context, lang=lang)


async def send_main_menu(
    update: Update, context: ContextTypes.DEFAULT_TYPE, lang: str = "pt"
) -> None:
    user = update.effective_user
    if not user:
        return

    name = user.first_name or "Parceiro"
    with get_db() as session:
        db_user = UserRepository.create_or_update(
            session, telegram_id=user.id, name=name, language=lang
        )
        couple = CoupleRepository.get_by_user_id(session, db_user.id)
        is_paired = couple is not None and couple.user_2_id is not None
        has_pending_invite = couple is not None and couple.user_2_id is None

    if lang == "en":
        greeting = (
            f"👋 Hello, {name}!\n\n"
            "I am your couple organization assistant.\n\n"
            "I can help you organize:\n"
            "📅 appointments\n"
            "⏰ reminders\n"
            "❤️ shared events\n\n"
        )
        if is_paired:
            greeting += "Choose an option from the menu below:"
        elif has_pending_invite:
            greeting += "You have an active couple invite! Share the code with your partner to connect."
        else:
            greeting += "To get started, link your couple using the options below:"
    else:
        greeting = (
            f"👋 Olá, {name}!\n\n"
            "Sou o assistente de organização de vocês.\n\n"
            "Posso ajudar a organizar:\n"
            "📅 compromissos\n"
            "⏰ lembretes\n"
            "❤️ eventos compartilhados\n\n"
        )
        if is_paired:
            greeting += "Escolha uma opção no menu abaixo:"
        elif has_pending_invite:
            greeting += "Você tem um convite de casal aberto! Compartilhe o código com sua parceira para se conectarem."
        else:
            greeting += "Para começarem, vinculem o casal usando as opções abaixo:"

    keyboard = get_main_menu_keyboard(
        is_paired=is_paired, has_pending_invite=has_pending_invite, lang=lang
    )

    if update.callback_query:
        await update.callback_query.edit_message_text(greeting, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(greeting, reply_markup=keyboard)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user:
        return

    name = user.first_name or "Parceiro"
    lang_already_selected = False
    if hasattr(context, "user_data") and isinstance(context.user_data, dict):
        lang_already_selected = context.user_data.get("lang_selected", False)

    with get_db() as session:
        db_user = UserRepository.get_by_telegram_id(session, user.id)
        if not db_user:
            db_user = UserRepository.create_or_update(
                session, telegram_id=user.id, name=name, language="pt"
            )
            is_first_interaction = True
        else:
            is_first_interaction = False
        user_lang = getattr(db_user, "language", "pt") or "pt"

    if is_first_interaction and not lang_already_selected:
        prompt_text = (
            f"👋 Olá, {name}! / Hello, {name}!\n\n"
            "Sou o assistente de organização de vocês.\n"
            "I am your couple assistant.\n\n"
            "🌐 Por favor, selecione seu idioma / Please choose your language:"
        )
        keyboard = get_language_selection_keyboard()
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(prompt_text, reply_markup=keyboard)
        elif update.message:
            await update.message.reply_text(prompt_text, reply_markup=keyboard)
        return

    await send_main_menu(update, context, lang=user_lang)
