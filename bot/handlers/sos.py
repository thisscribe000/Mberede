from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from core.models import User, get_db
from bot.keyboards.reply import registered_menu, guest_menu
from bot.utils.auth import verify_pin
from bot.utils.session import get_active_user


async def sos_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user, override = get_active_user(update.effective_user.id)

    if override:
        await update.message.reply_text(
            "❌ You can't send SOS while viewing another account.\n"
            "Use /switchback to return to your account first.",
        )
        return ConversationHandler.END

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return ConversationHandler.END

    if user.locked_until and user.locked_until > __import__("datetime").datetime.utcnow():
        await update.message.reply_text("🔒 Your account is temporarily locked. Try again later.")
        return ConversationHandler.END

    await update.message.reply_text("🔐 Enter your PIN to verify:")
    return 200


ASK_PIN = 200
ASK_CONTACTS = 201


async def verify_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    db = get_db()
    user, _ = get_active_user(update.effective_user.id)

    if not verify_pin(pin, user.pin_hash):
        user.failed_attempts += 1
        from datetime import timedelta
        if user.failed_attempts >= 5:
            user.locked_until = __import__("datetime").datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        await update.message.reply_text("❌ Incorrect PIN. Try again:")
        return ASK_PIN

    user.failed_attempts = 0
    user.last_accessed_at = __import__("datetime").datetime.utcnow()
    db.commit()

    contacts = db.query(__import__("core.models", fromlist=["EmergencyContact"]).EmergencyContact).filter(
        __import__("core.models", fromlist=["EmergencyContact"]).EmergencyContact.user_id == user.id
    ).order_by(__import__("core.models", fromlist=["EmergencyContact"]).EmergencyContact.priority).all()

    if not contacts:
        await update.message.reply_text("⚠️ You have no emergency contacts set up.", reply_markup=guest_menu())
        return ConversationHandler.END

    context.user_data["sos_user_id"] = user.id
    context.user_data["sos_contacts"] = contacts

    from bot.keyboards.reply import sos_contact_inline_keyboard
    await update.message.reply_text(
        "🚨 <b>SOS Alert</b>\n\nSelect a contact to notify:",
        parse_mode="HTML",
        reply_markup=sos_contact_inline_keyboard(contacts),
    )
    return ASK_CONTACTS


ASK_SOS_PIN = 200
ASK_SOS_CONTACTS = 201
ASK_SOS_LOCATION = 203


async def sos_contact_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.keyboards.reply import sos_contact_inline_keyboard, main_menu
    from core.sms import send_sos_sms
    from core.models import SOSLog, AccessLog

    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "back_to_main":
        await query.message.delete()
        return ConversationHandler.END

    if data == "sos_location":
        await query.message.edit_text(
            "📍 <b>Share Your Location</b>\n\nSend your current location so contacts know where to find you.\nTap the 📎 attachment button → Location.",
            parse_mode="HTML",
        )
        context.user_data["awaiting_location"] = True
        return ASK_SOS_LOCATION

    contacts = context.user_data.get("sos_contacts", [])
    message = context.user_data.get("sos_message", "I need help urgently! Please try to reach me or get help.")
    location = context.user_data.get("sos_location")

    if data == "sos_all":
        await _send_sos_to_contacts(update, context, contacts, message, location)
        return ConversationHandler.END

    if data.startswith("sos_contact:"):
        contact_id = data.split(":", 1)[1]
        selected = [c for c in contacts if c.id == contact_id]
        if selected:
            await _send_sos_to_contacts(update, context, selected, message, location)

    return ConversationHandler.END


async def _send_sos_to_contacts(update, context, contacts, message=None, location=None):
    from core.sms import send_sos_sms
    from core.models import SOSLog, AccessLog
    from bot.keyboards.reply import main_menu

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
            db.add(SOSLog(
                user_id=user.id,
                contact_id=contact.id,
                message=message,
                delivered=True,
                twilio_sid=result.get("message_id", ""),
            ))
            db.add(AccessLog(
                user_id=user.id,
                accessor_telegram_id=update.effective_user.id,
                action="sos_sent",
                contact_id=contact.id,
                success=True,
            ))
            results.append(f"✅ {contact.name}")
        except Exception:
            db.add(SOSLog(user_id=user.id, contact_id=contact.id, message=message, delivered=False))
            results.append(f"❌ {contact.name} (failed)")

    db.commit()

    response = "🚨 <b>SOS Sent!</b>\n\n" + "\n".join(results)
    if location:
        response += "\n\n📍 Location shared."
    await update.callback_query.message.edit_text(response, parse_mode="HTML")


async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_location"):
        return

    loc = update.message.location
    location_str = f"https://maps.google.com/?q={loc.latitude},{loc.longitude}"
    context.user_data["sos_location"] = location_str
    context.user_data["awaiting_location"] = False
    await update.message.reply_text(f"📍 Location saved!\n{location_str}\n\nSelect contacts to alert:")
    return ASK_SOS_CONTACTS


def get_sos_conversation():
    return ConversationHandler(
        entry_points=[CommandHandler("sos", sos_command)],
        states={
            ASK_SOS_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_pin)],
            ASK_SOS_CONTACTS: [CallbackQueryHandler(sos_contact_callback)],
            ASK_SOS_LOCATION: [MessageHandler(filters.LOCATION, handle_location)],
        },
        fallbacks=[],
        conversation_timeout=600,
    )


sos_contact_callback = sos_contact_callback
