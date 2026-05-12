from telegram import Update
from telegram.ext import ContextTypes

from core.models import User, get_db
from bot.keyboards.reply import registered_menu, guest_menu, switched_menu


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    from bot.utils.session import get_active_user
    active_user, override = get_active_user(update.effective_user.id)
    is_registered = active_user and active_user.pin_hash

    if override:
        guest = active_user
        await update.message.reply_text(
            "🔄 <b>Viewing Another Account</b>\n\n"
            "You're currently helping someone else access their contacts.\n"
            "Your account is untouched.\n\n"
            "Use /switchback to return to your account.\n"
            "This session expires in 2 hours.",
            parse_mode="HTML",
            reply_markup=switched_menu(),
        )
    elif is_registered:
        await update.message.reply_text(
            "👋 <b>Welcome back to Mberede!</b>\n\n"
            "Use /sos to alert your contacts.\n"
            "Use /emergency to help someone.\n"
            "Use /switch to view another person's account.",
            parse_mode="HTML",
            reply_markup=registered_menu(),
        )
    else:
        await update.message.reply_text(
            "👋 <b>Welcome to Mberede!</b>\n\n"
            "Register your account to save emergency contacts.\n"
            "Anyone can use /emergency to access contacts on any device.",
            parse_mode="HTML",
            reply_markup=guest_menu(),
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    from bot.utils.session import get_active_user
    active_user, override = get_active_user(update.effective_user.id)
    is_registered = active_user and active_user.pin_hash

    if override:
        text = (
            "<b>🔄 Guest Mode</b>\n\n"
            "You're viewing another person's contacts.\n"
            "Your account is untouched.\n\n"
            "/switchback — Return to your account\n"
            "/contacts — View their contacts\n"
            "/emergency — View contacts\n"
            "/help — This help"
        )
    elif is_registered:
        text = (
            "<b>Mberede Help</b>\n\n"
            "<b>Your Contacts:</b>\n"
            "/contacts — View your contacts\n"
            "/add — Add a contact\n"
            "/remove — Remove a contact\n\n"
            "<b>Emergency:</b>\n"
            "/sos — Alert your contacts\n"
            "/emergency — Help someone access their contacts\n"
            "/switch — View another person's account\n\n"
            "<b>Account:</b>\n"
            "/silent — Toggle panic mode\n"
            "/recover — Reset PIN\n"
            "/backupcard — Offline emergency card\n"
            "/export — Export your data\n"
            "/delete — Delete account\n"
            "/myid — Your Telegram ID\n"
            "/help — This message"
        )
    else:
        text = (
            "<b>Mberede Help</b>\n\n"
            "<b>Getting Started:</b>\n"
            "/register — Set up your account\n\n"
            "<b>Help Others:</b>\n"
            "/emergency — Enter someone's PIN to access their contacts\n\n"
            "<b>How it works:</b>\n"
            "1. Register and set a secret PIN\n"
            "2. Add your emergency contacts\n"
            "3. Lose your phone? Anyone can message this bot, enter your PIN, and contact your loved ones."
        )

    await update.message.reply_text(text, parse_mode="HTML")


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram User ID: <code>{update.effective_user.id}</code>",
        parse_mode="HTML",
    )
