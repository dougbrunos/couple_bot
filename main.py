import logging
import sys
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from app.config import config
from app.database.database import init_db
from app.bot.handlers.start import start_handler
from app.bot.handlers.help import help_handler
from app.bot.handlers.couple import create_couple_handler, get_join_couple_conversation_handler
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

# Configuração de logging estruturado
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def create_app():
    """Cria e configura a aplicação Telegram Bot."""
    # Valida variáveis de ambiente
    config.validate()

    # Inicializa banco de dados
    logger.info("Inicializando banco de dados...")
    init_db()

    # Constrói o bot
    app = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

    # ConversationHandlers (devem ser registrados antes de handlers genéricos)
    app.add_handler(get_add_event_conversation_handler())
    app.add_handler(get_join_couple_conversation_handler())

    # Comandos de navegação e menu
    app.add_handler(CommandHandler(["start", "menu"], start_handler))
    app.add_handler(CommandHandler(["help", "ajuda"], help_handler))
    app.add_handler(CallbackQueryHandler(start_handler, pattern="^menu_main$"))

    # Gestão de Casal
    app.add_handler(CommandHandler("criar_casal", create_couple_handler))
    app.add_handler(CallbackQueryHandler(create_couple_handler, pattern="^(menu_create_couple|menu_view_invite)$"))

    # Consultas de compromissos
    app.add_handler(CommandHandler("hoje", today_handler))
    app.add_handler(CallbackQueryHandler(today_handler, pattern="^menu_today$"))
    app.add_handler(CommandHandler("semana", week_handler))
    app.add_handler(CallbackQueryHandler(week_handler, pattern="^menu_week$"))
    app.add_handler(CommandHandler("eventos", events_list_handler))
    app.add_handler(CallbackQueryHandler(events_list_handler, pattern="^menu_events$"))

    # Exclusão de eventos
    app.add_handler(CommandHandler("delete", delete_menu_handler))
    app.add_handler(CallbackQueryHandler(delete_menu_handler, pattern="^menu_delete$"))
    app.add_handler(CallbackQueryHandler(confirm_delete_prompt_handler, pattern=r"^del_sel_\d+$"))
    app.add_handler(CallbackQueryHandler(execute_delete_handler, pattern=r"^del_confirm_\d+$"))

    # Ações em lembretes recebidos (OK e Adiar)
    app.add_handler(CallbackQueryHandler(reminder_ack_handler, pattern=r"^rem_ack_\d+$"))
    app.add_handler(CallbackQueryHandler(reminder_snooze_menu_handler, pattern=r"^rem_snooze_\d+$"))
    app.add_handler(CallbackQueryHandler(reminder_snooze_execute_handler, pattern=r"^snooze_do_\d+_\d+$"))
    app.add_handler(CallbackQueryHandler(reminder_snooze_cancel_handler, pattern=r"^snooze_cancel_\d+$"))

    # Agendador periódico de lembretes (a cada 30 segundos)
    if app.job_queue:
        app.job_queue.run_repeating(check_and_send_reminders, interval=30, first=5)
        logger.info("Scheduler de lembretes registrado no JobQueue (intervalo: 30s).")

    return app


def main():
    try:
        app = create_app()
        logger.info("Bot de Casal iniciado com sucesso! Aguardando mensagens (polling)...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Erro fatal ao iniciar aplicação: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
