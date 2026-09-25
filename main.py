import logging
import sys
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from app.config import config
from app.database.database import init_db
from app.bot.handlers.start import (
    start_handler,
    language_prompt_handler,
    set_language_callback_handler,
)
from app.bot.handlers.help import help_handler
from app.bot.handlers.couple import (
    create_couple_handler,
    get_join_couple_conversation_handler,
)
from app.bot.handlers.event import get_add_event_conversation_handler
from app.bot.handlers.query_handlers import today_handler, week_handler, events_list_handler
from app.bot.handlers.delete_handlers import (
    delete_menu_handler,
    confirm_delete_prompt_handler,
    execute_delete_handler,
)
from app.bot.handlers.reminder_handlers import (
    reminder_ack_handler,
    reminder_snooze_menu_handler,
    reminder_snooze_execute_handler,
    reminder_snooze_cancel_handler,
)
from app.scheduler.scheduler import check_and_send_reminders

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_app():
    config.validate()
    logger.info("Initializing database...")
    init_db()

    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # Conversation handlers
    app.add_handler(get_add_event_conversation_handler())
    app.add_handler(get_join_couple_conversation_handler())

    # Language selection
    app.add_handler(CommandHandler(["language", "idioma"], language_prompt_handler))
    app.add_handler(CallbackQueryHandler(set_language_callback_handler, pattern="^set_lang_(pt|en)$"))
    app.add_handler(CallbackQueryHandler(language_prompt_handler, pattern="^menu_change_lang$"))

    # Navigation and menu
    app.add_handler(CommandHandler(["start", "menu", "iniciar"], start_handler))
    app.add_handler(CommandHandler(["help", "ajuda"], help_handler))
    app.add_handler(CallbackQueryHandler(start_handler, pattern="^menu_main$"))

    # Couple management
    app.add_handler(CommandHandler(["criar_casal", "casal", "create_couple", "couple"], create_couple_handler))
    app.add_handler(CallbackQueryHandler(create_couple_handler, pattern="^(menu_create_couple|menu_view_invite)$"))

    # Schedule queries
    app.add_handler(CommandHandler(["hoje", "today"], today_handler))
    app.add_handler(CallbackQueryHandler(today_handler, pattern="^menu_today$"))
    app.add_handler(CommandHandler(["semana", "week"], week_handler))
    app.add_handler(CallbackQueryHandler(week_handler, pattern="^menu_week$"))
    app.add_handler(CommandHandler(["eventos", "events", "listar", "list"], events_list_handler))
    app.add_handler(CallbackQueryHandler(events_list_handler, pattern="^menu_events$"))

    # Event deletion
    app.add_handler(CommandHandler(["delete", "deletar", "excluir", "remover", "remove"], delete_menu_handler))
    app.add_handler(CallbackQueryHandler(delete_menu_handler, pattern="^menu_delete$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_prompt_handler, pattern=r"^del_sel_\d+$"))
    app.add_handler(CallbackQueryHandler(execute_delete_handler, pattern=r"^del_confirm_\d+$"))

    # Reminder actions
    app.add_handler(CallbackQueryHandler(reminder_ack_handler, pattern=r"^rem_ack_\d+$"))
    app.add_handler(CallbackQueryHandler(reminder_snooze_menu_handler, pattern=r"^rem_snooze_\d+$"))
    app.add_handler(CallbackQueryHandler(reminder_snooze_execute_handler, pattern=r"^snooze_do_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(reminder_snooze_cancel_handler, pattern=r"^snooze_cancel_\d+$"))

    if app.job_queue:
        app.job_queue.run_repeating(check_and_send_reminders, interval=30, first=5)
        logger.info("Reminder scheduler registered in JobQueue (interval: 30s).")

    return app


def main():
    try:
        app = create_app()
        logger.info("Couple Bot started successfully. Listening for updates...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Fatal error starting application: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
