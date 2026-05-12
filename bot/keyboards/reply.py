from telegram import KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup


def registered_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("/contacts")],
        [KeyboardButton("/sos")],
        [KeyboardButton("/add")],
        [KeyboardButton("/remove")],
        [KeyboardButton("/emergency")],
        [KeyboardButton("/help")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Select an option")


def guest_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("/register")],
        [KeyboardButton("/emergency")],
        [KeyboardButton("/help")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Select an option")


def switched_menu() -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton("/contacts")],
        [KeyboardButton("/emergency")],
        [KeyboardButton("/switchback")],
        [KeyboardButton("/help")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, input_field_placeholder="Select an option")


def main_menu() -> ReplyKeyboardMarkup:
    return guest_menu()


def contact_inline_keyboard(contacts: list) -> InlineKeyboardMarkup:
    keyboard = []
    for i, contact in enumerate(contacts):
        keyboard.append([
            InlineKeyboardButton(
                f"{i+1}. {contact.name} ({contact.relationship_ or 'Contact'})",
                callback_data=f"view_contact:{contact.id}",
            )
        ])
    keyboard.append([
        InlineKeyboardButton("🔙 Back", callback_data="back_to_main"),
    ])
    return InlineKeyboardMarkup(keyboard)


def sos_contact_inline_keyboard(contacts: list) -> InlineKeyboardMarkup:
    keyboard = []
    for contact in contacts:
        keyboard.append([
            InlineKeyboardButton(
                f"📞 {contact.name}",
                callback_data=f"sos_contact:{contact.id}",
            )
        ])
    keyboard.append([
        InlineKeyboardButton("📢 Send to All", callback_data="sos_all"),
        InlineKeyboardButton("📍 Share Location", callback_data="sos_location"),
        InlineKeyboardButton("🔙 Cancel", callback_data="back_to_main"),
    ])
    return InlineKeyboardMarkup(keyboard)


def contact_action_keyboard(contact_id: str, contact_phone: str, contact_name: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"📞 {contact_name}: {contact_phone}",
                url=f"tel:{contact_phone}",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 Telegram Call",
                switch_inline_query=f"call {contact_phone}",
            )
        ],
        [
            InlineKeyboardButton(
                "☁️ Server Call (VoIP)",
                callback_data=f"voip_call:{contact_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "💬 SMS",
                callback_data=f"view_contact:{contact_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🚨 Send SOS SMS",
                callback_data=f"sos_contact:{contact_id}",
            )
        ],
        [
            InlineKeyboardButton(
                "🗑️ Remove Contact",
                callback_data=f"delete_contact:{contact_id}",
            )
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_main"),
        ],
    ])


def yes_no_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes", callback_data=yes_data),
            InlineKeyboardButton("❌ No", callback_data=no_data),
        ]
    ])


def empty_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([], resize_keyboard=True)
