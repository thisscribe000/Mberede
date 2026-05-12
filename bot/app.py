import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from core.config import config
from core.models import init_db
from bot.handlers.start import start_command, help_command, myid_command
from bot.handlers.register import get_register_conversation
from bot.handlers.emergency import (
    get_emergency_conversation,
    view_contact_callback,
    delete_contact_callback,
    voip_call_callback,
)
from bot.handlers.sos import get_sos_conversation, sos_contact_callback
from bot.handlers.contacts import get_contact_handlers
from bot.handlers.admin import silent_command, delete_account_command
from bot.handlers.analytics import get_admin_handlers
from bot.handlers.recovery import get_recovery_conversation
from bot.handlers.offline import backupcard_command
from bot.handlers.export import get_export_handlers
from bot.handlers.verify import get_verify_handlers
from bot.handlers.switch import get_switch_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, config.log_level),
)
log = logging.getLogger(__name__)


def create_app():
    init_db()

    app = (
        Application.builder()
        .token(config.telegram_bot_token)
        .build()
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid_command))

    app.add_handler(get_register_conversation())
    app.add_handler(get_emergency_conversation())
    app.add_handler(get_sos_conversation())

    for handler in get_contact_handlers():
        app.add_handler(handler)

    app.add_handler(CommandHandler("silent", silent_command))
    app.add_handler(CommandHandler("delete", delete_account_command))
    app.add_handler(get_recovery_conversation())
    app.add_handler(CommandHandler("backupcard", backupcard_command))

    for handler in get_export_handlers():
        app.add_handler(handler)

    for handler in get_verify_handlers():
        app.add_handler(handler)

    for handler in get_switch_handlers():
        app.add_handler(handler)

    for handler in get_admin_handlers():
        app.add_handler(handler)

    app.add_handler(CallbackQueryHandler(view_contact_callback))
    app.add_handler(CallbackQueryHandler(delete_contact_callback))
    app.add_handler(CallbackQueryHandler(sos_contact_callback))
    app.add_handler(CallbackQueryHandler(voip_call_callback))

    log.info("Mberede bot initialized")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run_polling(drop_pending_updates=True)
