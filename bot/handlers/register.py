from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from core.models import User, get_db
from bot.utils.auth import hash_pin, verify_pin
from bot.utils.validators import validate_pin, validate_phone, validate_name, sanitize_input
from bot.utils.rate import rate_limiter
from bot.keyboards.reply import main_menu
from bot.keyboards.reply import contact_inline_keyboard, yes_no_keyboard


(
    ASK_NAME,
    ASK_PIN,
    CONFIRM_PIN,
    ASK_FIRST_CONTACT_NAME,
    ASK_CONTACT_PHONE,
    ASK_CONTACT_RELATIONSHIP,
    ASK_ADD_ANOTHER,
) = range(7)


async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if user and user.pin_hash:
        await update.message.reply_text(
            "You already have an account. Use /settings to manage your account or /contacts to view your contacts.",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 <b>Let's set up your Mberede account.</b>\n\n"
        "This PIN will be used by anyone who finds your device to access your emergency contacts.\n\n"
        "<b>Create a secret PIN (4-6 digits):</b>",
        parse_mode="HTML",
    )
    return ASK_PIN


async def ask_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    valid, msg = validate_pin(pin)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nPlease enter a 4-6 digit PIN:")
        return ASK_PIN

    context.user_data["reg_pin"] = pin
    await update.message.reply_text("✅ PIN accepted.\n\n<b>Please confirm your PIN:</b>", parse_mode="HTML")
    return CONFIRM_PIN


async def confirm_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    if pin != context.user_data.get("reg_pin"):
        await update.message.reply_text("❌ PINs do not match. Let's start over.\n\nPlease enter a 4-6 digit PIN:")
        return ASK_PIN

    pin_hash = hash_pin(pin)
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user:
        user = User(
            telegram_user_id=update.effective_user.id,
            telegram_username=update.effective_user.username,
            pin_hash=pin_hash,
        )
        db.add(user)
    else:
        user.pin_hash = pin_hash
        user.telegram_username = update.effective_user.username

    db.commit()
    context.user_data.clear()

    await update.message.reply_text(
        "🔐 PIN set successfully!\n\n"
        "Now let's add your first emergency contact.\n\n"
        "<b>Enter the contact's name:</b>",
        parse_mode="HTML",
    )
    return ASK_FIRST_CONTACT_NAME


async def ask_contact_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = sanitize_input(update.message.text)
    valid, msg = validate_name(name)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nPlease enter the contact's name:")
        return ASK_FIRST_CONTACT_NAME

    context.user_data["contact_name"] = name
    await update.message.reply_text(
        f"👤 <b>{name}</b>\n\nEnter their phone number (with country code, e.g. +2348012345678):",
        parse_mode="HTML",
    )
    return ASK_CONTACT_PHONE


async def ask_contact_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    valid, msg, formatted = validate_phone(phone)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nPlease enter a valid phone number with country code:")
        return ASK_CONTACT_PHONE

    from core.models import EmergencyContact, User
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    existing = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == user.id,
        EmergencyContact.phone == formatted,
    ).first()
    if existing:
        await update.message.reply_text(
            f"❌ This contact is already in your list.\n\nEnter a different phone number:",
        )
        return ASK_CONTACT_PHONE

    context.user_data["contact_phone"] = formatted

    keyboard = [
        ["Spouse", "Parent", "Sibling"],
        ["Friend", "Child", "Doctor"],
        ["Employer", "Other"],
    ]
    from telegram import ReplyKeyboardMarkup
    await update.message.reply_text(
        f"📱 <b>{context.user_data['contact_name']}</b>\nPhone: {formatted}\n\n"
        "Select their relationship:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[k for k in row] for row in keyboard],
            input_field_placeholder="Select relationship",
        ),
    )
    return ASK_CONTACT_RELATIONSHIP


async def ask_relationship(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from core.models import EmergencyContact, User
    rel = update.message.text.strip()
    if not rel:
        await update.message.reply_text("Please select or type a relationship:")
        return ASK_CONTACT_RELATIONSHIP

    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    contact_count = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).count()

    if contact_count >= 5:
        await update.message.reply_text("⚠️ You have reached the maximum of 5 contacts.", reply_markup=main_menu())
        context.user_data.clear()
        return ConversationHandler.END

    contact = EmergencyContact(
        user_id=user.id,
        name=context.user_data["contact_name"],
        phone=context.user_data["contact_phone"],
        relationship_=rel,
        priority=contact_count + 1,
    )
    db.add(contact)
    db.commit()

    contact_name = context.user_data["contact_name"]
    contact_phone = contact.phone

    keyboard = [
        ["+ Add Another", "I'm Done"],
    ]
    from telegram import ReplyKeyboardMarkup
    await update.message.reply_text(
        f"✅ <b>Contact saved!</b>\n\n"
        f"👤 {contact_name} ({rel})\n"
        f"📱 {contact_phone}\n\n"
        "Would you like to add another contact?",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardMarkup(
            [[k for k in row] for row in keyboard],
            input_field_placeholder="Add another?",
        ),
    )
    return ASK_ADD_ANOTHER


async def ask_add_another(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text.strip() == "+ Add Another":
        context.user_data.clear()
        await update.message.reply_text("👤 Enter the next contact's name:")
        return ASK_FIRST_CONTACT_NAME
    else:
        await update.message.reply_text(
            "🎉 <b>You're all set!</b>\n\n"
            "Your emergency contacts are ready.\n"
            "If your phone is lost or stolen, anyone can message this bot and enter your PIN to reach your loved ones.\n\n"
            "Use /contacts to manage your contacts.\n"
            "Use /sos to send an emergency alert.\n"
            "Use /backupcard to generate a printable offline card.",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Registration cancelled. Use /register to start over.")
    return ConversationHandler.END


def get_register_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("register", register_command)],
        states={
            ASK_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pin)],
            CONFIRM_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_pin)],
            ASK_FIRST_CONTACT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact_name)],
            ASK_CONTACT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact_phone)],
            ASK_CONTACT_RELATIONSHIP: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_relationship)],
            ASK_ADD_ANOTHER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_add_another)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
