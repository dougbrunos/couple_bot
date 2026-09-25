from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.utils.i18n import t


def get_language_selection_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("🇧🇷 Português", callback_data="set_lang_pt"),
            InlineKeyboardButton("🇺🇸 English", callback_data="set_lang_en"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_main_menu_keyboard(
    is_paired: bool = False, has_pending_invite: bool = False, lang: str = "pt"
) -> InlineKeyboardMarkup:
    if not is_paired:
        buttons = []
        if has_pending_invite:
            buttons.append(
                [
                    InlineKeyboardButton(
                        t("btn_view_invite", lang), callback_data="menu_view_invite"
                    )
                ]
            )
        else:
            buttons.append(
                [
                    InlineKeyboardButton(
                        t("btn_create_couple", lang), callback_data="menu_create_couple"
                    )
                ]
            )
        buttons.append(
            [
                InlineKeyboardButton(
                    t("btn_join_couple", lang), callback_data="menu_join_couple"
                )
            ]
        )
        buttons.append(
            [
                InlineKeyboardButton(
                    t("btn_language", lang), callback_data="menu_change_lang"
                )
            ]
        )
        return InlineKeyboardMarkup(buttons)

    keyboard = [
        [
            InlineKeyboardButton(
                t("btn_add_event", lang), callback_data="menu_add_event"
            )
        ],
        [
            InlineKeyboardButton(t("btn_today", lang), callback_data="menu_today"),
            InlineKeyboardButton(t("btn_week", lang), callback_data="menu_week"),
        ],
        [
            InlineKeyboardButton(t("btn_events", lang), callback_data="menu_events"),
            InlineKeyboardButton(t("btn_delete", lang), callback_data="menu_delete"),
        ],
        [
            InlineKeyboardButton(
                t("btn_language", lang), callback_data="menu_change_lang"
            )
        ],
    ]
    return InlineKeyboardMarkup(keyboard)
