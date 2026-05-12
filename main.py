#!/usr/bin/env python3
import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bot.app import create_app
from web_dashboard import create_flask_app
from core.config import config

app = create_app()

flask_app = create_flask_app()


def run_flask():
    flask_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))

    if os.getenv("RUN_WEB", "false").lower() == "true":
        flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
    else:
        app.run_polling(drop_pending_updates=True)
