import io
import json
import base64
import secrets
from datetime import datetime
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler

from core.models import User, EmergencyContact, RecoveryCode, get_db
from bot.keyboards.reply import main_menu


async def backupcard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = get_db()
    user = db.query(User).filter(User.telegram_user_id == update.effective_user.id).first()

    if not user or not user.pin_hash:
        await update.message.reply_text("❌ You need to register first. Use /register.")
        return

    contacts = db.query(EmergencyContact).filter(EmergencyContact.user_id == user.id).order_by(EmergencyContact.priority).all()

    if not contacts:
        await update.message.reply_text("⚠️ Add at least one contact before generating a backup card.", reply_markup=main_menu())
        return

    verification_token = secrets.token_hex(16)

    payload = {
        "v": 1,
        "uid": user.telegram_user_id,
        "mid": verification_token,
        "ts": datetime.utcnow().isoformat(),
        "bot": "Mberede",
    }
    encoded = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    qr_text = f"mberede://verify?d={encoded}"

    card_text = (
        "╔══════════════════════════════════════╗\n"
        "║     🚨 MBEREDE EMERGENCY CARD 🚨     ║\n"
        "╠══════════════════════════════════════╣\n"
        f"║  Owner: {user.telegram_username or 'Mberede User'}\n"
        "╠══════════════════════════════════════╣\n"
        "║  EMERGENCY CONTACTS:                ║\n"
    )

    for i, contact in enumerate(contacts):
        card_text += f"║  {i+1}. {contact.name:<20s}            ║\n"
        card_text += f"║     {contact.phone:<20s}            ║\n"
        if contact.relationship:
            card_text += f"║     ({contact.relationship})\n"

    card_text += (
        "╠══════════════════════════════════════╣\n"
        "║  HOW TO USE:                        ║\n"
        "║  1. Open Telegram                   ║\n"
        "║  2. Search for this bot             ║\n"
        "║  3. Send /emergency                ║\n"
        "║  4. Enter owner's secret PIN       ║\n"
        "║  5. Access emergency contacts       ║\n"
        "╠══════════════════════════════════════╣\n"
        "║  FOR FINDERS:                       ║\n"
        "║  Scan QR or open bot to contact     ║\n"
        "║  the owner's loved ones.           ║\n"
        "╚══════════════════════════════════════╝\n"
        f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
    )

    await update.message.reply_text(
        "🪪 <b>Offline Emergency Backup Card</b>\n\n"
        "Print this card and keep it in your wallet or with important documents.\n"
        "Anyone who finds your device can use this to contact your loved ones — even without internet access.",
        parse_mode="HTML",
    )

    try:
        import qrcode
        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(qr_text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        buf.name = "mberede_emergency_qr.png"

        await update.message.reply_photo(
            photo=InputFile(buf),
            caption=f"📱 Scan this QR code with any phone camera to open Mberede.",
        )
    except ImportError:
        pass

    await update.message.reply_text(f"<pre>{card_text}</pre>", parse_mode="HTML")
    await update.message.reply_text(
        "💡 <b>Tip:</b> Print this card and keep it with your ID.\n"
        "This works even when your phone is offline.",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )
