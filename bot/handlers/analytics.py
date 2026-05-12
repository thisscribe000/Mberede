from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler

from core.models import User, EmergencyContact, AccessLog, SOSLog, get_db
from core.config import config


def is_admin(telegram_id: int) -> bool:
    return telegram_id in config.admin_telegram_ids


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Admin access only.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton("📊 Overview", callback_data="admin_overview")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users")],
        [InlineKeyboardButton("🚨 SOS Events", callback_data="admin_sos")],
        [InlineKeyboardButton("🔐 Access Logs", callback_data="admin_access")],
        [InlineKeyboardButton("🚨 SOS Stats", callback_data="admin_sos_stats")],
        [InlineKeyboardButton("⚙️ Actions", callback_data="admin_actions")],
    ]

    await update.message.reply_text(
        "🛡️ <b>Mberede Admin Panel</b>\n\n"
        "Welcome, Administrator. Select an option:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    db = get_db()

    if data == "admin_overview":
        total_users = db.query(User).count()
        active_users = db.query(User).filter(User.pin_hash != None).count()
        total_contacts = db.query(EmergencyContact).count()
        verified_contacts = db.query(EmergencyContact).filter(EmergencyContact.is_verified == True).count()
        total_sos = db.query(SOSLog).count()
        sos_delivered = db.query(SOSLog).filter(SOSLog.delivered == True).count()
        sos_today = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow().replace(hour=0, minute=0, second=0)).count()
        sos_this_week = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow() - timedelta(days=7)).count()
        new_users_today = db.query(User).filter(User.created_at > datetime.utcnow().replace(hour=0, minute=0, second=0)).count()
        new_users_week = db.query(User).filter(User.created_at > datetime.utcnow() - timedelta(days=7)).count()
        locked_users = db.query(User).filter(User.locked_until != None, User.locked_until > datetime.utcnow()).count()

        text = (
            "📊 <b>System Overview</b>\n\n"
            f"<b>Users:</b>\n"
            f"  Total registered: {total_users}\n"
            f"  Active (PIN set): {active_users}\n"
            f"  New today: {new_users_today}\n"
            f"  New this week: {new_users_week}\n"
            f"  Locked accounts: {locked_users}\n\n"
            f"<b>Contacts:</b>\n"
            f"  Total contacts: {total_contacts}\n"
            f"  Verified contacts: {verified_contacts}\n\n"
            f"<b>SOS Activity:</b>\n"
            f"  Total SOS sent: {total_sos}\n"
            f"  Delivered: {sos_delivered}\n"
            f"  Today: {sos_today}\n"
            f"  This week: {sos_this_week}\n"
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

    elif data == "admin_users":
        users = db.query(User).filter(User.pin_hash != None).order_by(User.created_at.desc()).limit(50).all()
        if not users:
            await query.message.edit_text("No users found.", reply_markup=admin_back_kb())
            return

        text = f"👥 <b>Recent Users ({len(users)})</b>\n\n"
        for u in users:
            status = "🔒" if (u.locked_until and u.locked_until > datetime.utcnow()) else "✅"
            contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == u.id).count()
            last = _time_ago(u.last_accessed_at)
            text += f"{status} @{u.telegram_username or u.telegram_user_id} — {contacts} contacts — {last}\n"

        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

    elif data == "admin_sos":
        sos_logs = db.query(SOSLog).order_by(SOSLog.sent_at.desc()).limit(20).all()
        if not sos_logs:
            await query.message.edit_text("No SOS events yet.", reply_markup=admin_back_kb())
            return

        text = "🚨 <b>Recent SOS Events</b>\n\n"
        for log in sos_logs:
            contact = db.query(EmergencyContact).filter(EmergencyContact.id == log.contact_id).first()
            status = "✅" if log.delivered else "❌"
            time_ago = _time_ago(log.sent_at)
            name = contact.name if contact else "Unknown"
            text += f"{status} {time_ago} — {name}\n"

        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

    elif data == "admin_sos_stats":
        sos_total = db.query(SOSLog).count()
        sos_delivered = db.query(SOSLog).filter(SOSLog.delivered == True).count()
        sos_today = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow() - timedelta(hours=24)).count()
        sos_week = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow() - timedelta(days=7)).count()
        sos_month = db.query(SOSLog).filter(SOSLog.sent_at > datetime.utcnow() - timedelta(days=30)).count()
        rate = (sos_delivered / sos_total * 100) if sos_total > 0 else 0
        active_users = db.query(User).filter(User.pin_hash != None).count()
        engaged = db.query(SOSLog.user_id).distinct().count()
        engagement = (engaged / active_users * 100) if active_users > 0 else 0

        text = (
            "🚨 <b>SOS Statistics</b>\n\n"
            f"<b>Volume:</b>\n  Today: {sos_today} | Week: {sos_week} | Month: {sos_month} | All: {sos_total}\n\n"
            f"<b>Delivery:</b>\n  Delivered: {sos_delivered} | Rate: {rate:.1f}%\n\n"
            f"<b>Engagement:</b>\n  Users who sent SOS: {engaged}/{active_users} ({engagement:.1f}%)"
        )
        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

    elif data == "admin_access":
        logs = db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(20).all()
        if not logs:
            await query.message.edit_text("No access logs yet.", reply_markup=admin_back_kb())
            return

        text = "🔐 <b>Recent Access Logs</b>\n\n"
        for log in logs:
            status = "✅" if log.success else "❌"
            text += f"{status} {_time_ago(log.timestamp)} — {log.action}\n"

        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

    elif data == "admin_actions":
        keyboard = [
            [InlineKeyboardButton("📋 List All Users", callback_data="admin_list_users")],
            [InlineKeyboardButton("🗑️ Clear Old Logs", callback_data="admin_clear_logs")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
        ]
        await query.message.edit_text(
            "⚙️ <b>Admin Actions</b>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data == "admin_list_users":
        users = db.query(User).filter(User.pin_hash != None).all()
        text = f"📋 <b>All Users ({len(users)})</b>\n\n"
        for i, u in enumerate(users):
            contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == u.id).count()
            last = _time_ago(u.last_accessed_at) if u.last_accessed_at else "Never"
            text += f"{i+1}. <code>{u.telegram_user_id}</code> — @{u.telegram_username or 'no username'} — {contacts} contacts — last active {last}\n"

        await query.message.edit_text(text, parse_mode="HTML", reply_markup=admin_back_kb())

    elif data == "admin_clear_logs":
        cutoff = datetime.utcnow() - timedelta(days=90)
        deleted = db.query(AccessLog).filter(AccessLog.timestamp < cutoff).delete()
        db.commit()
        await query.message.edit_text(
            f"✅ Cleared {deleted} log entries older than 90 days.",
            reply_markup=admin_back_kb(),
        )

    elif data == "admin_back":
        await admin_command(update, context)
        return

    return


def admin_back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Admin", callback_data="admin_back")]])


def get_admin_handlers():
    return [
        CommandHandler("admin", admin_command),
        CallbackQueryHandler(admin_callback, pattern="^admin_"),
    ]


def _time_ago(dt: datetime) -> str:
    if not dt:
        return "Never"
    diff = datetime.utcnow() - dt
    if diff.total_seconds() < 60:
        return "Just now"
    elif diff.total_seconds() < 3600:
        return f"{int(diff.total_seconds() / 60)}m ago"
    elif diff.total_seconds() < 86400:
        return f"{int(diff.total_seconds() / 3600)}h ago"
    else:
        return f"{int(diff.total_seconds() / 86400)}d ago"
