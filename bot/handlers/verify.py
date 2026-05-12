import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from core.models import User, EmergencyContact, get_db
from core.sms import send_sos_sms
from bot.keyboards.reply import main_menu
from bot.utils.validators import validate_phone


ASK_CONTACT_VERIFY = 400
ASK_CONTACT_CODE = 401


async def verify_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return ConversationHandler.END

    contacts = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == user.id,
        EmergencyContact.is_verified == False,
    ).all()

    if not contacts:
        await update.message.reply_text(
            "✅ All your contacts have been verified!",
            reply_markup=main_menu(),
        )
        return ConversationHandler.END

    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    keyboard = [
        [InlineKeyboardButton(f"📱 {c.name} ({c.phone})", callback_data=f"verify_select:{c.id}")]
        for c in contacts
    ]
    keyboard.append([InlineKeyboardButton("🔙 Cancel", callback_data="verify_cancel")])

    await update.message.reply_text(
        "<b>Contact Verification</b>\n\n"
        "Verify that your emergency contacts consent to being contacted in emergencies.\n"
        "We'll send them an SMS to confirm.\n\n"
        "Select a contact to verify:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def verify_select_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "verify_cancel":
        await query.message.edit_text("❌ Cancelled.")
        return ConversationHandler.END

    if not data.startswith("verify_select:"):
        return

    contact_id = data.split(":", 1)[1]
    db = get_db()
    contact = db.query(EmergencyContact).filter(EmergencyContact.id == contact_id).first()

    if not contact:
        await query.message.edit_text("❌ Contact not found.")
        return ConversationHandler.END

    context.user_data["verify_contact_id"] = contact_id

    import secrets
    code = str(secrets.randbelow(900000) + 100000)
    context.user_data["verify_code"] = code
    contact.verification_code = code
    contact.verification_expires = __import__("datetime").datetime.utcnow() + __import__("datetime").timedelta(minutes=15)
    db.commit()

    try:
        send_sos_sms(
            contact_phone=contact.phone,
            user_name="Mberede",
            message=f"Someone is trying to add you as an emergency contact on Mberede.\n"
                    f"If this is expected, reply with: {code}\n"
                    f"If not, ignore this message.",
        )
        await query.message.edit_text(
            f"✅ Verification SMS sent to {contact.name}!\n\n"
            "Ask them to reply with the code they receive via SMS.",
            parse_mode="HTML",
        )
        return ASK_CONTACT_CODE
    except Exception as e:
        await query.message.edit_text(f"❌ Could not send SMS: {e}")
        return ConversationHandler.END


async def verify_code_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip()
    db = get_db()
    contact = db.query(EmergencyContact).filter(
        EmergencyContact.id == context.user_data["verify_contact_id"]
    ).first()

    if not contact or contact.verification_code != code:
        await update.message.reply_text("❌ Invalid code. Try /verify to start over.")
        return ConversationHandler.END

    from datetime import datetime, timedelta
    if datetime.utcnow() > contact.verification_expires:
        await update.message.reply_text("❌ Code expired. Try /verify to start over.")
        return ConversationHandler.END

    contact.is_verified = True
    contact.consent_obtained = True
    contact.consent_at = datetime.utcnow()
    contact.verification_code = None
    db.commit()

    await update.message.reply_text(
        f"✅ {contact.name} has been verified!\n"
        "They have consented to being contacted in emergencies.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


def get_verify_handlers():
    return [
        CommandHandler("verify", verify_contact_command),
        CallbackQueryHandler(verify_select_contact, pattern="^verify_"),
        MessageHandler(filters.TEXT & ~filters.COMMAND, verify_code_entry),
    ]
