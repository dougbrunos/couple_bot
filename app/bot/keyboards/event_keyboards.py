from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.utils.i18n import t


def get_cancel_event_keyboard(lang: str = "pt") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel_event")]]
    )


def get_participant_keyboard(
    user_name: str = "Eu", partner_name: str = "Ela", lang: str = "pt"
) -> InlineKeyboardMarkup:
    shared_label = t("scope_shared", lang)
    cancel_label = t("btn_cancel", lang)
    keyboard = [
        [
            InlineKeyboardButton(f"👤 {user_name}", callback_data="scope_personal"),
            InlineKeyboardButton(f"👥 {partner_name}", callback_data="scope_partner"),
        ],
        [InlineKeyboardButton(shared_label, callback_data="scope_shared")],
        [InlineKeyboardButton(cancel_label, callback_data="cancel_event")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_recurrence_keyboard(lang: str = "pt") -> InlineKeyboardMarkup:
    cancel_label = t("btn_cancel", lang)
    keyboard = [
        [
            InlineKeyboardButton(t("recur_none", lang), callback_data="recur_none"),
            InlineKeyboardButton(t("recur_daily", lang), callback_data="recur_daily"),
        ],
        [
            InlineKeyboardButton(t("recur_weekly", lang), callback_data="recur_weekly"),
            InlineKeyboardButton(t("recur_monthly", lang), callback_data="recur_monthly"),
        ],
        [InlineKeyboardButton(t("recur_yearly", lang), callback_data="recur_yearly")],
        [InlineKeyboardButton(cancel_label, callback_data="cancel_event")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_reminder_keyboard(lang: str = "pt") -> InlineKeyboardMarkup:
    cancel_label = t("btn_cancel", lang)
    keyboard = [
        [
            InlineKeyboardButton(t("remind_none", lang), callback_data="remind_none"),
            InlineKeyboardButton(t("remind_10m", lang), callback_data="remind_10"),
        ],
        [
            InlineKeyboardButton(t("remind_30m", lang), callback_data="remind_30"),
            InlineKeyboardButton(t("remind_1h", lang), callback_data="remind_60"),
        ],
        [
            InlineKeyboardButton(t("remind_1d", lang), callback_data="remind_1440"),
        ],
        [InlineKeyboardButton(cancel_label, callback_data="cancel_event")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirm_event_keyboard(lang: str = "pt") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t("btn_confirm", lang), callback_data="confirm_event_save"),
                InlineKeyboardButton(t("btn_cancel", lang), callback_data="cancel_event"),
            ]
        ]
    )
