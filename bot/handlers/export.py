import json
import csv
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from core.models import User, EmergencyContact, AccessLog, SOSLog, RecoveryCode, get_db
from bot.keyboards.reply import main_menu


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    await update.message.reply_text(
        "📤 <b>Data Export</b>\n\nChoose export format:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📄 JSON", callback_data="export_json")],
            [InlineKeyboardButton("📊 CSV", callback_data="export_csv")],
            [InlineKeyboardButton("🔙 Cancel", callback_data="export_cancel")],
        ]),
    )


async def export_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "export_cancel":
        await query.message.edit_text("❌ Export cancelled.", reply_markup=main_menu())
        return

    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).all()
    access_logs = db.query(AccessLog).filter(AccessLog.user_id == user.id).all()
    sos_logs = db.query(SOSLog).filter(SOSLog.user_id == user.id).all()

    if data == "export_json":
        payload = {
            "exported_at": datetime.utcnow().isoformat(),
            "user": {
                "telegram_user_id": user.telegram_user_id,
                "telegram_username": user.telegram_username,
                "created_at": user.created_at.isoformat() if user.created_at else None,
            },
            "emergency_contacts": [
                {
                    "name": c.name,
                    "phone": c.phone,
                    "relationship": c.relationship_,
                    "priority": c.priority,
                    "is_verified": c.is_verified,
                    "consent_obtained": c.consent_obtained,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in contacts
            ],
            "access_logs": [
                {
                    "action": log.action,
                    "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                    "success": log.success,
                }
                for log in access_logs[-50:]
            ],
            "sos_logs": [
                {
                    "sent_at": log.sent_at.isoformat() if log.sent_at else None,
                    "delivered": log.delivered,
                }
                for log in sos_logs[-50:]
            ],
        }

        content = json.dumps(payload, indent=2)
        buf = io.BytesIO(content.encode())
        buf.name = f"mberede_export_{datetime.utcnow().strftime('%Y%m%d')}.json"

        await query.message.edit_text("📄 JSON export ready.")
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=InputFile(buf),
            filename=buf.name,
            caption="Your Mberede data export (JSON).",
        )

    elif data == "export_csv":
        buf = io.StringIO()
        writer = csv.writer(buf)

        writer.writerow(["Emergency Contacts"])
        writer.writerow(["Name", "Phone", "Relationship", "Priority", "Verified", "Consent", "Created At"])
        for c in contacts:
            writer.writerow([c.name, c.phone, c.relationship_, c.priority, c.is_verified, c.consent_obtained, c.created_at])

        writer.writerow([])
        writer.writerow(["Access Logs"])
        writer.writerow(["Action", "Timestamp", "Success"])
        for log in access_logs[-50:]:
            writer.writerow([log.action, log.timestamp, log.success])

        writer.writerow([])
        writer.writerow(["SOS Logs"])
        writer.writerow(["Sent At", "Delivered"])
        for log in sos_logs[-50:]:
            writer.writerow([log.sent_at, log.delivered])

        buf_content = io.BytesIO(buf.getvalue().encode())
        buf_content.name = f"mberede_export_{datetime.utcnow().strftime('%Y%m%d')}.csv"

        await query.message.edit_text("📊 CSV export ready.")
        await context.bot.send_document(
            chat_id=update.effective_user.id,
            document=InputFile(buf_content),
            filename=buf_content.name,
            caption="Your Mberede data export (CSV).",
        )


def get_export_handlers():
    return [
        CommandHandler("export", export_command),
        CallbackQueryHandler(export_callback, pattern="^export_"),
    ]
