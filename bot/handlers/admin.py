from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from core.models import User, get_db
from bot.keyboards.reply import main_menu


async def silent_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    user.silent_mode = not user.silent_mode
    db.commit()

    status = "enabled" if user.silent_mode else "disabled"
    await update.message.reply_text(
        f"🔇 Silent mode {status}.\n"
        "Bot responses will be minimal.",
        reply_markup=main_menu(),
    )


async def delete_account_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    if context.args:
        pin = " ".join(context.args).strip()
    else:
        await update.message.reply_text("⚠️ This will permanently delete all your data.\n\nTo confirm, type: /delete YOUR_PIN")
        return

    if not verify_pin := __import__("bot.utils.auth", fromlist=["verify_pin"]).verify_pin(pin, user.pin_hash):
        await update.message.reply_text("❌ Incorrect PIN.")
        return

    db.delete(user)
    db.commit()
    await update.message.reply_text("🗑️ Account and all data deleted. We're sorry to see you go.")
