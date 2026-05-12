from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards.reply import main_menu


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 <b>Welcome to Mberede!</b>\n\n"
        "<i>Reach your loved ones when it matters most.</i>\n\n"
        "If you found a device, use /emergency to access the owner's emergency contacts.\n"
        "If you're setting up your account, use /register.\n\n"
        "Type /help for more information.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "<b>Mberede Help</b>\n\n"
        "<b>Commands:</b>\n"
        "/start — Restart the bot\n"
        "/register — Set up your emergency contacts\n"
        "/emergency — Access emergency contacts (device finder)\n"
        "/sos — Send emergency alert to your contacts\n"
        "/contacts — View your emergency contacts\n"
        "/add — Add a new contact\n"
        "/remove — Remove a contact\n"
        "/myid — Get your Telegram user ID\n"
        "/settings — Manage your settings\n"
        "/silent — Toggle silent mode\n"
        "/delete — Delete your account\n"
        "/help — Show this help message\n\n"
        "<b>How it works:</b>\n"
        "1. Register and set a secret PIN\n"
        "2. Add your emergency contacts\n"
        "3. If your phone is lost/stolen, anyone can message this bot, enter your PIN, and contact your loved ones.\n\n"
        "Your PIN is hashed and never stored in plain text.",
        parse_mode="HTML",
    )


async def myid_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Your Telegram User ID: <code>{update.effective_user.id}</code>",
        parse_mode="HTML",
    )
