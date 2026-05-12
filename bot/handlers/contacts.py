from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from core.models import User, EmergencyContact, get_db
from bot.utils.auth import verify_pin
from bot.keyboards.reply import contact_inline_keyboard, main_menu


async def contacts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).order_by(EmergencyContact.priority).all()

    if not contacts:
        await update.message.reply_text(
            "📋 You have no emergency contacts.\n\nUse /add to add one.",
            reply_markup=main_menu(),
        )
        return

    await update.message.reply_text(
        "📋 <b>Your Emergency Contacts:</b>",
        parse_mode="HTML",
        reply_markup=contact_inline_keyboard(contacts),
    )


async def add_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from bot.handlers.register import (
        ASK_FIRST_CONTACT_NAME, ASK_CONTACT_PHONE, ASK_CONTACT_RELATIONSHIP, ASK_ADD_ANOTHER,
    )
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return ConversationHandler.END

    if user.pin_hash:
        pin = update.message.text.strip()
        if not verify_pin(pin, user.pin_hash):
            await update.message.reply_text("❌ Incorrect PIN.")
            return ConversationHandler.END

    count = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).count()
    if count >= 5:
        await update.message.reply_text("⚠️ Maximum 5 contacts reached.", reply_markup=main_menu())
        return ConversationHandler.END

    await update.message.reply_text("👤 Enter the contact's name:")
    return ASK_FIRST_CONTACT_NAME


async def remove_contact_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    if context.args:
        name_query = " ".join(context.args).strip().lower()
    else:
        await update.message.reply_text("Usage: /remove <contact name>\n\nYour contacts:")
        contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).all()
        for c in contacts:
            await update.message.reply_text(f"• {c.name} ({c.relationship or 'Contact'})")
        return

    contact = db.query(EmergencyContact).filter(
        EmergencyContact.user_id == user.id,
        EmergencyContact.name.ilike(f"%{name_query}%"),
    ).first()

    if not contact:
        await update.message.reply_text(f"❌ No contact found matching '{name_query}'.")
        return

    db.delete(contact)
    db.commit()
    await update.message.reply_text(f"🗑️ {contact.name} has been removed.", reply_markup=main_menu())
