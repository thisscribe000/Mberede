from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from core.models import User, EmergencyContact, AccessLog, get_db
from bot.utils.auth import verify_pin, is_account_locked
from bot.utils.rate import rate_limiter
from bot.utils.validators import validate_pin
from bot.keyboards.reply import contact_inline_keyboard, contact_action_keyboard


ASK_EMERGENCY_PIN = 100


async def emergency_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚨 <b>Emergency Access</b>\n\n"
        "If you found a lost or stolen device, enter the owner's secret PIN to view their emergency contacts.\n\n"
        "<b>Enter the PIN:</b>",
        parse_mode="HTML",
    )
    return ASK_EMERGENCY_PIN


async def verify_emergency_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    valid, msg = validate_pin(pin)
    if not valid:
        await update.message.reply_text("❌ Invalid PIN format. Please enter 4-6 digits:")
        return ASK_EMERGENCY_PIN

    db = get_db()

    all_users = db.query(User).filter(User.is_active == True).all()
    matched_user = None

    for user in all_users:
        if user.pin_hash and not is_account_locked(user.locked_until):
            if verify_pin(pin, user.pin_hash):
                matched_user = user
                break

    log = AccessLog(
        accessor_telegram_id=update.effective_user.id,
        action="emergency_access_attempt",
        success=False,
    )

    if matched_user:
        log.user_id = matched_user.id
        log.success = True
        log.action = "viewed_contact"
        matched_user.last_accessed_at = __import__("datetime").datetime.utcnow()
        db.commit()

        contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == matched_user.id).order_by(EmergencyContact.priority).all()

        if not contacts:
            await update.message.reply_text("⚠️ No emergency contacts have been set up yet.")
            return ConversationHandler.END

        context.user_data["emergency_user_id"] = matched_user.id
        await update.message.reply_text(
            "✅ PIN verified!\n\n<b>Emergency Contacts:</b>",
            parse_mode="HTML",
        )
        await update.message.reply_text(
            "Select a contact:",
            reply_markup=contact_inline_keyboard(contacts),
        )
        return ASK_EMERGENCY_PIN
    else:
        rate_limiter.record_attempt(update.effective_user.id)

        for user in all_users:
            if user.pin_hash:
                user.failed_attempts += 1
                if user.failed_attempts >= 5:
                    from datetime import timedelta
                    user.locked_until = __import__("datetime").datetime.utcnow() + timedelta(minutes=15)

        db.commit()
        log.action = "emergency_access_failed"
        db.add(log)
        db.commit()

        locked = rate_limiter.is_locked(update.effective_user.id)
        wait = rate_limiter.wait_time(update.effective_user.id)

        if locked:
            await update.message.reply_text(
                f"❌ Too many failed attempts. Please wait {wait} seconds.",
                parse_mode="HTML",
            )
            return ConversationHandler.END

        await update.message.reply_text(
            "❌ Incorrect PIN. Please try again:",
        )
        return ASK_EMERGENCY_PIN


async def view_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        await query.message.delete()
        return ConversationHandler.END

    if not data.startswith("view_contact:"):
        return

    contact_id = data.split(":", 1)[1]
    db = get_db()
    contact = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id).first()

    if not contact:
        await query.message.edit_text("❌ Contact not found.")
        return

    await query.message.edit_text(
        f"👤 <b>{contact.name}</b>\n"
        f"📱 {contact.phone}\n"
        f"💼 {contact.relationship or 'Contact'}",
        parse_mode="HTML",
        reply_markup=contact_action_keyboard(contact_id),
    )


async def delete_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not query.data.startswith("delete_contact:"):
        return

    contact_id = query.data.split(":", 1)[1]
    db = get_db()
    contact = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id).first()

    if contact:
        db.delete(contact)
        db.commit()

    await query.message.edit_text("🗑️ Contact removed.")


def get_emergency_conversation() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("emergency", emergency_command)],
        states={
            ASK_EMERGENCY_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_emergency_pin)],
        },
        fallbacks=[],
        conversation_timeout=600,
    )
