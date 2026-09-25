from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_cancel_event_keyboard() -> InlineKeyboardMarkup:
    """Botão para cancelar a criação de evento."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_event")]])


def get_participant_keyboard(user_name: str = "Eu", partner_name: str = "Ela") -> InlineKeyboardMarkup:
    """Botões de seleção de participante/escopo do evento."""
    keyboard = [
        [
            InlineKeyboardButton(f"👤 {user_name}", callback_data="scope_personal"),
            InlineKeyboardButton(f"👩 {partner_name}", callback_data="scope_partner"),
        ],
        [InlineKeyboardButton("❤️ Nós dois", callback_data="scope_shared")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_event")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_recurrence_keyboard() -> InlineKeyboardMarkup:
    """Botões de seleção de regra de recorrência."""
    keyboard = [
        [
            InlineKeyboardButton("Não", callback_data="recur_none"),
            InlineKeyboardButton("Diariamente", callback_data="recur_daily"),
        ],
        [
            InlineKeyboardButton("Semanalmente", callback_data="recur_weekly"),
            InlineKeyboardButton("Mensalmente", callback_data="recur_monthly"),
        ],
        [InlineKeyboardButton("Anualmente", callback_data="recur_yearly")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_event")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reminder_keyboard() -> InlineKeyboardMarkup:
    """Botões de seleção de antecedência de lembrete."""
    keyboard = [
        [
            InlineKeyboardButton("Sem lembrete", callback_data="remind_none"),
            InlineKeyboardButton("10 min antes", callback_data="remind_10"),
        ],
        [
            InlineKeyboardButton("30 min antes", callback_data="remind_30"),
            InlineKeyboardButton("1 hora antes", callback_data="remind_60"),
        ],
        [
            InlineKeyboardButton("1 dia antes", callback_data="remind_1440"),
        ],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_event")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_event_keyboard() -> InlineKeyboardMarkup:
    """Botões de confirmação final da criação do evento."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Confirmar", callback_data="confirm_event_save"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_event"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
