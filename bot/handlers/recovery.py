import io
import secrets
import base64
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from core.models import User, EmergencyContact, RecoveryCode, get_db
from bot.utils.auth import hash_pin, generate_recovery_code
from bot.keyboards.reply import main_menu


ASK_PIN = 300
ASK_RECOVERY_CODE = 301


async def recovery_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔑 <b>Account Recovery</b>\n\n"
        "Forgot your PIN? You can reset it using a recovery code.\n\n"
        "<b>Enter your PIN to verify you own this account:</b>",
        parse_mode="HTML",
    )
    return ASK_PIN


async def ask_pin_for_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.utils.auth import verify_pin

    pin = update.message.text.strip()
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return ConversationHandler.END

    if not verify_pin(pin, user.pin_hash):
        await update.message.reply_text("❌ Incorrect PIN. Use /help to contact support if you've lost access.")
        return ConversationHandler.END

    codes = db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.used == False,
        RecoveryCode.expires_at > datetime.utcnow(),
    ).all()

    if not codes:
        recovery_codes = []
        for _ in range(5):
            code = generate_recovery_code()
            expiry = datetime.utcnow() + timedelta(days=30)
            rc = RecoveryCode(
                user_id=user.id,
                code=code,
                expires_at=expiry,
            )
            db.add(rc)
            recovery_codes.append(code)

        db.commit()

        await update.message.reply_text(
            "📋 <b>Your Recovery Codes</b>\n\n"
            "Write these down and keep them safe! Each code can only be used once.\n\n"
            + "\n".join(f"• <code>{code}</code>" for code in recovery_codes) +
            "\n\n⚠️ Store these codes securely. You'll need them if you forget your PIN.",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    context.user_data["recovery_user_id"] = user.id
    await update.message.reply_text(
        f"📋 You have {len(codes)} unused recovery code(s).\n\n<b>Enter one of your recovery codes:</b>",
        parse_mode="HTML",
    )
    return ASK_RECOVERY_CODE


async def verify_recovery_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    db = get_db()
    user = db.query(User).filter(User.id == context.user_data["recovery_user_id"]).first()

    rc = db.query(RecoveryCode).filter(
        RecoveryCode.user_id == user.id,
        RecoveryCode.code == code,
        RecoveryCode.used == False,
        RecoveryCode.expires_at > datetime.utcnow(),
    ).first()

    if not rc:
        await update.message.reply_text("❌ Invalid or expired recovery code. Try again:")
        return ASK_RECOVERY_CODE

    rc.used = True
    db.commit()

    await update.message.reply_text("✅ Recovery code accepted!\n\n<b>Create a new PIN (4-6 digits):</b>", parse_mode="HTML")
    context.user_data["new_pin_pending"] = True
    return ASK_PIN


async def reset_pin_with_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.utils.validators import validate_pin, hash_pin

    pin = update.message.text.strip()
    valid, msg = validate_pin(pin)
    if not valid:
        await update.message.reply_text(f"❌ {msg}\n\nEnter a 4-6 digit PIN:")
        return ASK_PIN

    db = get_db()
    user = db.query(User).filter(User.id == context.user_data["recovery_user_id"]).first()
    user.pin_hash = hash_pin(pin)
    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    context.user_data.clear()

    await update.message.reply_text(
        "🔐 PIN reset successful!\n\nYou can now use /emergency with your new PIN.",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def cancel_recovery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Recovery cancelled.")
    return ConversationHandler.END


def get_recovery_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("recover", recovery_command)],
        states={
            ASK_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pin_for_recovery)],
            ASK_RECOVERY_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_recovery_code)],
        },
        fallbacks=[CommandHandler("cancel", cancel_recovery)],
        conversation_timeout=300,
    )
