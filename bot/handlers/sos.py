from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from core.models import User, EmergencyContact, SOSLog, AccessLog, get_db
from bot.utils.auth import verify_pin, is_account_locked
from bot.keyboards.reply import sos_contact_inline_keyboard, main_menu
from core.sms import send_sos_sms


ASK_SOS_PIN = 200
ASK_SOS_CONTACTS = 201
ASK_SOS_MESSAGE = 202
ASK_SOS_LOCATION = 203


async def sos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return ConversationHandler.END

    if is_account_locked(user.locked_until):
        await update.message.reply_text("🔒 Your account is temporarily locked. Try again later.")
        return ConversationHandler.END

    await update.message.reply_text("🔐 Enter your PIN to verify:")
    return ASK_SOS_PIN


async def verify_sos_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not verify_pin(pin, user.pin_hash):
        user.failed_attempts += 1
        from datetime import timedelta
        if user.failed_attempts >= 5:
            user.locked_until = __import__("datetime").datetime.utcnow() + timedelta(minutes=15)
        db.commit()

        AccessLog(
            user_id=user.id,
            accessor_telegram_id=update.effective_user.id,
            action="sos_pin_failed",
            success=False,
        )
        db.commit()
        await update.message.reply_text("❌ Incorrect PIN. Try again:")
        return ASK_SOS_PIN

    user.failed_attempts = 0
    user.last_accessed_at = __import__("datetime").datetime.utcnow()
    db.commit()

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).order_by(EmergencyContact.priority).all()

    if not contacts:
        await update.message.reply_text("⚠️ You have no emergency contacts set up.", reply_markup=main_menu())
        return ConversationHandler.END

    context.user_data["sos_user_id"] = user.id
    context.user_data["sos_contacts"] = contacts

    await update.message.reply_text(
        f"🚨 <b>SOS Alert</b>\n\nSelect a contact to notify:",
        parse_mode="HTML",
        reply_markup=sos_contact_inline_keyboard(contacts),
    )
    return ASK_SOS_CONTACTS


async def sos_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        await query.message.delete()
        return ConversationHandler.END

    if data == "sos_location":
        await query.message.edit_text(
            "📍 <b>Share Your Location</b>\n\n"
            "Send your current location so contacts know where to find you.\n"
            "Tap the 📎 attachment button → Location.",
            parse_mode="HTML",
        )
        context.user_data["awaiting_location"] = True
        return ASK_SOS_LOCATION

    if data == "sos_all":
        contacts = context.user_data.get("sos_contacts", [])
        message = context.user_data.get("sos_message", "I need help urgently! Please try to reach me or get help.")
        location = context.user_data.get("sos_location")
        await _send_sos_to_contacts(update, context, contacts, message, location)
        return ConversationHandler.END

    if data.startswith("sos_contact:"):
        contact_id = data.split(":", 1)[1]
        contacts = context.user_data.get("sos_contacts", [])
        message = context.user_data.get("sos_message", "I need help urgently! Please try to reach me or get help.")
        location = context.user_data.get("sos_location")
        selected = [c for c in contacts if c.id == contact_id]
        if selected:
            await _send_sos_to_contacts(update, context, selected, message, location)

    return ConversationHandler.END


async def _send_sos_to_contacts(update, context, contacts, message=None, location=None):
    db = get_db()
    user = db.query(User).filter(User.id == context.user_data["sos_user_id"]).first()
    user_name = update.effective_user.full_name or "Someone"

    if message is None:
        message = "I need help urgently! Please try to reach me or get help."

    results = []
    for contact in contacts:
        try:
            result = send_sos_sms(
                contact_phone=contact.phone,
                user_name=user_name,
                message=message,
                location=location,
            )
            sos_log = SOSLog(
                user_id=user.id,
                contact_id=contact.id,
                message=message,
                delivered=True,
                twilio_sid=result.get("message_id", ""),
            )
            db.add(sos_log)

            AccessLog(
                user_id=user.id,
                accessor_telegram_id=update.effective_user.id,
                action="sos_sent",
                contact_id=contact.id,
                success=True,
            )
            results.append(f"✅ {contact.name}")
        except Exception as e:
            sos_log = SOSLog(user_id=user.id, contact_id=contact.id, message=message, delivered=False)
            db.add(sos_log)
            results.append(f"❌ {contact.name} (failed)")

    db.commit()

    response = "🚨 <b>SOS Sent!</b>\n\n" + "\n".join(results)
    if location:
        response += f"\n\n📍 Location shared."
    await update.callback_query.message.edit_text(response, parse_mode="HTML")
    await context.bot.send_message(
        chat_id=update.effective_user.id,
        text="Use /sos anytime to send another alert.",
        reply_markup=main_menu(),
    )


def get_sos_conversation() -> ConversationHandler:
    from telegram import Location
    from telegram.ext import MessageHandler

    async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not context.user_data.get("awaiting_location"):
            return

        loc = update.message.location
        lat = loc.latitude
        lon = loc.longitude
        location_str = f"https://maps.google.com/?q={lat},{lon}"

        context.user_data["sos_location"] = location_str
        context.user_data["awaiting_location"] = False

        contacts = context.user_data.get("sos_contacts", [])
        message = context.user_data.get("sos_message", "I need help urgently!")
        await update.message.reply_text(
            f"📍 Location saved!\n{location_str}\n\nNow select contacts to alert:",
        )
        return ASK_SOS_CONTACTS

    return ConversationHandler(
        entry_points=[CommandHandler("sos", sos_command)],
        states={
            ASK_SOS_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_sos_pin)],
            ASK_SOS_CONTACTS: [
                CallbackQueryHandler(sos_contact_callback),
            ],
            ASK_SOS_LOCATION: [
                MessageHandler(filters.LOCATION, handle_location),
            ],
        },
        fallbacks=[],
        conversation_timeout=600,
    )
