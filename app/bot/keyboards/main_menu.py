from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_main_menu_keyboard(is_paired: bool = False, has_pending_invite: bool = False) -> InlineKeyboardMarkup:
    """Retorna o teclado inline principal dependendo se o usuário já possui um parceiro vinculado."""
    if not is_paired:
        buttons = []
        if has_pending_invite:
            buttons.append([InlineKeyboardButton("❤️ Ver código do convite", callback_data="menu_view_invite")])
        else:
            buttons.append([InlineKeyboardButton("❤️ Criar casal", callback_data="menu_create_couple")])
        buttons.append([InlineKeyboardButton("🔗 Entrar em um casal", callback_data="menu_join_couple")])
        return InlineKeyboardMarkup(buttons)

    # Menu para casal conectado
    keyboard = [
        [InlineKeyboardButton("➕ Novo evento", callback_data="menu_add_event")],
        [
            InlineKeyboardButton("📅 Hoje", callback_data="menu_today"),
            InlineKeyboardButton("🗓 Semana", callback_data="menu_week"),
        ],
        [
            InlineKeyboardButton("📋 Eventos", callback_data="menu_events"),
            InlineKeyboardButton("🗑 Excluir", callback_data="menu_delete"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
