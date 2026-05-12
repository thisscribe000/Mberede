from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler

from core.models import User, EmergencyContact, get_db
from bot.keyboards.reply import main_menu, contact_inline_keyboard
from bot.utils.validators import validate_name, validate_phone, sanitize_input
from bot.utils.auth import verify_pin


async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).order_by(EmergencyContact.priority).all()

    if not contacts:
        await update.message.reply_text(
            "📋 You have no emergency contacts.\n\nUse /add to add one.",
            reply_markup=main_menu(),
        )
        return

    text = "📋 <b>Your Emergency Contacts:</b>\n\n"
    for i, c in enumerate(contacts):
        text += f"{i+1}. {c.name} — {c.phone} ({c.relationship_ or 'Contact'})\n"

    text += "\nSelect a contact to view details:"
    await update.message.reply_text(text, parse_mode="HTML", reply_markup=contact_inline_keyboard(contacts))


(AWAIT_NAME, AWAIT_PHONE, AWAIT_REL) = range(50, 53)


async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return ConversationHandler.END

    count = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).count()
    if count >= 5:
        await update.message.reply_text("⚠️ Maximum of 5 contacts reached.", reply_markup=main_menu())
        return ConversationHandler.END

    await update.message.reply_text(
        "👤 <b>Add Emergency Contact</b>\n\nEnter the contact's name:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="add_cancel")]]),
    )
    return AWAIT_NAME


async def add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = sanitize_input(update.message.text)
    valid, msg = validate_name(name)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nEnter the contact's name:")
        return AWAIT_NAME

    context.user_data["add_name"] = name
    await update.message.reply_text(
        f"👤 <b>{name}</b>\n\nEnter their phone number (with country code, e.g. +2348012345678):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="add_cancel")]]),
    )
    return AWAIT_PHONE


async def add_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    valid, msg, formatted = validate_phone(phone)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nEnter a valid phone number with country code:")
        return AWAIT_PHONE

    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()
    existing = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == user.id,
        EmergencyContact.phone == formatted,
    ).first()
    if existing:
        await update.message.reply_text("❌ This contact is already in your list.\n\nEnter a different phone number:")
        return AWAIT_PHONE

    context.user_data["add_phone"] = formatted

    keyboard = [
        ["Spouse", "Parent", "Sibling"],
        ["Friend", "Child", "Doctor"],
        ["Employer", "Other"],
    ]
    from telegram import ReplyKeyboardMarkup
    await update.message.reply_text(
        f"📱 <b>{context.user_data['add_name']}</b>\nPhone: {formatted}\n\nSelect their relationship:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return AWAIT_REL


async def add_rel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rel = update.message.text.strip()
    if not rel:
        await update.message.reply_text("Please select or type a relationship:")
        return AWAIT_REL

    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()
    count = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).count()

    contact = EmergencyContact(
        user_id=user.id,
        name=context.user_data["add_name"],
        phone=context.user_data["add_phone"],
        relationship_=rel,
        priority=count + 1,
    )
    db.add(contact)
    db.commit()
    context.user_data.clear()

    await update.message.reply_text(
        f"✅ <b>Contact added!</b>\n\n"
        f"👤 {contact.name} ({rel})\n"
        f"📱 {contact.phone}\n\n"
        "Use /contacts to view all your contacts.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def add_cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.message.edit_text("❌ Contact addition cancelled.")
    return ConversationHandler.END


async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).order_by(EmergencyContact.priority).all()

    if not contacts:
        await update.message.reply_text("📋 You have no contacts to remove.", reply_markup=main_menu())
        return

    keyboard = [
        [InlineKeyboardButton(f"🗑️ {c.name}", callback_data=f"remove_confirm:{c.id}")]
        for c in contacts
    ]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="remove_cancel")])

    await update.message.reply_text(
        "🗑️ <b>Remove Contact</b>\n\nSelect a contact to remove:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def remove_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "remove_cancel":
        await query.message.edit_text("Cancelled.", reply_markup=main_menu())
        return

    if data.startswith("remove_confirm:"):
        contact_id = data.split(":", 1)[1]
        db = get_db()
        contact = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id).first()

        if contact:
            name = contact.name
            db.delete(contact)
            db.commit()
            await query.message.edit_text(
                f"🗑️ <b>{name}</b> has been removed.",
                parse_mode="HTML",
            )
        else:
            await query.message.edit_text("❌ Contact not found.")


def get_contact_handlers():
    return [
        CommandHandler("contacts", contacts_command),
        ConversationHandler(
            entry_points=[CommandHandler("add", add_command)],
            states={
                AWAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_name)],
                AWAIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_phone)],
                AWAIT_REL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rel)],
            },
            fallbacks=[CallbackQueryHandler(add_cancel_callback, pattern="^add_cancel$")],
        ),
        CommandHandler("remove", remove_command),
        CallbackQueryHandler(remove_callback, pattern="^(remove_confirm:|remove_cancel$)"),
    ]


from telegram.ext import CallbackQueryHandler
