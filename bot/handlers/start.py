from telegram import Update
from telegram.ext import ContextTypes

from core.models import User, get_db
from bot.keyboards.reply import registered_menu, guest_menu


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()
    is_registered = user and user.pin_hash

    if is_registered:
        await update.message.reply_text(
            "👋 <b>Welcome back to Mberede!</b>\n\n"
            "<i>Reach your loved ones when it matters most.</i>\n\n"
            "You have your emergency contacts set up.\n"
            "Use /sos to alert your contacts.\n"
            "Use /emergency if someone found a device.\n\n"
            "Use /help for all commands.",
            parse_mode="HTML",
            reply_markup=registered_menu(),
        )
    else:
        await update.message.reply_text(
            "👋 <b>Welcome to Mberede!</b>\n\n"
            "<i>Reach your loved ones when it matters most.</i>\n\n"
            "If you found a device, use /emergency to access the owner's emergency contacts.\n"
            "If you're setting up your account, use /register.\n\n"
            "Use /help for more information.",
            parse_mode="HTML",
            reply_markup=guest_menu(),
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()
    is_registered = user and user.pin_hash

    if is_registered:
        text = (
            "<b>Mberede Help</b>\n\n"
            "<b>Your Contacts:</b>\n"
            "/contacts — View your emergency contacts\n"
            "/add — Add a new contact\n"
            "/remove — Remove a contact\n\n"
            "<b>Emergency:</b>\n"
            "/emergency — Access contacts (for someone who found a device)\n"
            "/sos — Send emergency alert to your contacts\n\n"
            "<b>Account:</b>\n"
            "/silent — Toggle silent/panic mode\n"
            "/recover — Reset PIN using recovery codes\n"
            "/backupcard — Generate printable offline emergency card\n"
            "/export — Export your data\n"
            "/delete — Delete your account\n"
            "/myid — Get your Telegram user ID\n"
            "/help — Show this help message\n\n"
            "<b>Quick reminder:</b>\n"
            "Your PIN protects your contacts. Anyone with your PIN can access them."
        )
    else:
        text = (
            "<b>Mberede Help</b>\n\n"
            "<b>Getting Started:</b>\n"
            "/register — Set up your PIN and emergency contacts\n"
            "/emergency — Access contacts (device finder)\n\n"
            "<b>Commands:</b>\n"
            "/help — Show this help message\n\n"
            "<b>How it works:</b>\n"
            "1. Register and set a secret PIN\n"
            "2. Add your emergency contacts\n"
            "3. If your phone is lost/stolen, anyone can message this bot, enter your PIN, and contact your loved ones.\n\n"
            "Your PIN is hashed — never stored in plain text."
        )


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram User ID: <code>{update.effective_user.id}</code>",
        parse_mode="HTML",
    )
