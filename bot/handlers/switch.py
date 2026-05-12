from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from core.models import User, EmergencyContact, SessionOverride, get_db
from bot.keyboards.reply import (
    switched_menu, guest_menu, contact_inline_keyboard,
)
from bot.utils.auth import verify_pin


ASK_SWITCH_PIN = 300


async def switch_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    _, override = _get_active_user(db, update.effective_user.id)

    if override:
        await update.message.reply_text(
            "⚠️ You are currently viewing another person's account.\n"
            "Use /switchback to return to your account first.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Return to My Account", callback_data="do_switchback"),
                InlineKeyboardButton("❌ Stay Here", callback_data="stay_switched"),
            ]]),
        )
        return

    my_user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()
    if not my_user or not my_user.pin_hash:
        await update.message.reply_text("❌ You need to register your own account first. Use /register.")
        return

    await update.message.reply_text(
        "🔄 <b>Switch Account</b>\n\n"
        "You're about to access a different Mberede account.\n"
        "You'll see that person's contacts and can help them reach their loved ones.\n\n"
        "Your account is NOT affected — you can switch back anytime.\n\n"
        "<b>Enter the account owner's PIN:</b>",
        parse_mode="HTML",
    )
    return ASK_SWITCH_PIN


async def ask_switch_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pin = update.message.text.strip()
    db = get_db()

    all_users = db.query(User).filter(User.is_active == True, User.pin_hash != None).all()
    matched = None
    for u in all_users:
        if u.telegram_user_id == update.effective_user.id:
            continue
        if verify_pin(pin, u.pin_hash):
            matched = u
            break

    if not matched:
        await update.message.reply_text(
            "❌ No account found with that PIN.\n\n"
            "Make sure you're entering the PIN of the account owner, not your own.\n\n"
            "Enter the PIN:",
            parse_mode="HTML",
        )
        return ASK_SWITCH_PIN

    my_user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    db.query(SessionOverride).filter(
        SessionOverride.telegram_user_id == update.effective_user.id
    ).delete()

    override = SessionOverride(
        telegram_user_id=update.effective_user.id,
        original_user_id=my_user.id if my_user else None,
        guest_user_id=matched.id,
        expires_at=datetime.utcnow() + timedelta(hours=2),
    )
    db.add(override)
    db.commit()

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == matched.id).order_by(EmergencyContact.priority).all()

    if contacts:
        await update.message.reply_text(
            f"🔄 <b>Viewing {matched.telegram_username or 'Account'}</b>\n\n"
            f"You can now see {matched.telegram_username or 'this person'}'s contacts.\n"
            "Your account is safe.\n"
            "Use /switchback anytime to return.\n\n"
            "Select a contact:",
            parse_mode="HTML",
            reply_markup=contact_inline_keyboard(contacts),
        )
    else:
        await update.message.reply_text(
            f"🔄 <b>Viewing {matched.telegram_username or 'Account'}</b>\n\n"
            "This account has no emergency contacts set up yet.\n"
            "Use /switchback to return to your account.",
            parse_mode="HTML",
            reply_markup=guest_menu(),
        )

    return ConversationHandler.END


async def switchback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    _, override = _get_active_user(db, update.effective_user.id)

    if not override:
        await update.message.reply_text(
            "✅ You are already on your own account.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 View My Contacts", callback_data="show_contacts"),
            ]]),
        )
        return

    db.delete(override)
    db.commit()

    await update.message.reply_text(
        "✅ <b>Back to Your Account</b>\n\n"
        "You're back to managing your own Mberede account.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 View My Contacts", callback_data="show_contacts"),
        ]]),
    )


async def switchback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "do_switchback":
        db = get_db()
        override = db.query(SessionOverride).filter(
            SessionOverride.telegram_user_id == update.effective_user.id,
        ).first()
        if override:
            db.delete(override)
            db.commit()
        await query.message.edit_text(
            "✅ Back to your account.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 View My Contacts", callback_data="show_contacts"),
            ]]),
        )
        return

    if data == "stay_switched":
        await query.message.edit_text("Okay, staying on the guest account.")
        return


def _get_active_user(db, telegram_user_id):
    override = db.query(SessionOverride).filter(
        SessionOverride.telegram_user_id == telegram_user_id,
        SessionOverride.expires_at > datetime.utcnow(),
    ).first()

    if override:
        user = db.query(User).filter(User.id == override.guest_user_id).first()
        return user, override

    user = db.query(User).filter(User.telegram_user_id == telegram_user_id).first()
    return user, None


def get_switch_handlers():
    return [
        CommandHandler("switch", switch_command),
        CommandHandler("switchback", switchback_command),
        CallbackQueryHandler(switchback_callback, pattern="^(do_switchback|stay_switched)$"),
        ConversationHandler(
            entry_points=[CommandHandler("switch", switch_command)],
            states={
                ASK_SWITCH_PIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_switch_pin)],
            },
            fallbacks=[CommandHandler("cancel", lambda u, c: ConversationHandler.END)],
        ),
    ]
