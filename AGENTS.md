# Mberede — Agent Context for Next Session

## What This Project Is
Mberede is an emergency contact access system built around a Telegram bot.
The core use case: your phone is lost/stolen, you meet a stranger, they open the Telegram bot,
enter your secret PIN, and can call/SMS your emergency contacts — or send an SOS.

The system also supports a `/switch` command so one device can temporarily view
another person's account without logging out.

## Tech Stack
- **Language:** Python 3.14
- **Telegram Bot:** python-telegram-bot v22+
- **Database:** SQLite (SQLAlchemy ORM) — ready for PostgreSQL
- **SMS/VoIP:** Twilio + Africa's Talking (via `core/sms.py`, `core/voip.py`)
- **Web Dashboard:** Flask (optional, runs on port 5000 at `/web`)
- **Dependencies:** See `requirements.txt`

## Key Files
| File | Purpose |
|------|---------|
| `bot/app.py` | Main bot entry — all handlers registered here |
| `core/models.py` | SQLAlchemy models (User, EmergencyContact, AccessLog, SOSLog, RecoveryCode, SessionOverride) |
| `core/config.py` | Environment config dataclass |
| `bot/utils/session.py` | `get_active_user()` — respects `/switch` override |
| `bot/handlers/start.py` | Dynamic menus: guest/registered/switched state |
| `bot/handlers/switch.py` | `/switch` and `/switchback` (session override) |
| `bot/handlers/emergency.py` | `/emergency` finder flow |
| `bot/handlers/sos.py` | `/sos` works BOTH own account AND switched |
| `bot/handlers/contacts.py` | `/add`, `/remove`, `/contacts` |
| `bot/handlers/analytics.py` | `/admin` panel for admin users |
| `web_dashboard.py` | Flask web analytics (run with `RUN_WEB=true`) |
| `PLAN.md` | Full project plan from the beginning |
| `index.html` | Landing page (static HTML) |

## Database — Important: Column Name `relationship_`
The `EmergencyContact` model's relationship column is named `relationship_`
(not `relationship`) because `relationship` conflicts with SQLAlchemy's ORM method.
All references to contact relationships in handlers and keyboards use `contact.relationship_`.

## Multi-Account Design
- User identity = Telegram User ID (not phone, not device)
- `/switch PIN` creates a `SessionOverride` row → `get_active_user()` returns the guest account
- `SessionOverride` expires after 2 hours
- While switched: `/add`, `/remove` blocked; `/contacts`, `/sos`, `/emergency` work (read-only or SOS-sending)
- `/switchback` deletes the override and returns to own account

## Admin Access
- Controlled by `ADMIN_TELEGRAM_IDS` in `.env` (comma-separated Telegram IDs)
- Get your ID via `/myid` command
- `/admin` shows: overview, users, SOS events, access logs, actions
- Web dashboard at `/web/admin` (optional, run with `RUN_WEB=true`)

## Running Locally
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
# Edit .env with TELEGRAM_BOT_TOKEN, ADMIN_TELEGRAM_IDS, SMS credentials
./venv/bin/python3.14 main.py
```

With web dashboard:
```bash
RUN_WEB=true ./venv/bin/python3.14 main.py
```

## Environment Variables
```
TELEGRAM_BOT_TOKEN=...
ADMIN_TELEGRAM_IDS=123456,789012
DATABASE_URL=sqlite:///./mberede.db
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=...
AFRICAS_TALKING_API_KEY=...
AFRICAS_TALKING_USERNAME=...
SECRET_KEY=...
SMS_PROVIDER=twilio  # or africas_talking
LOG_LEVEL=INFO
```

## Known Issues Fixed
- Python 3.14 + SQLAlchemy 2.0.25 compatibility: upgraded to SQLAlchemy 2.0.35+
- `Mapped[...]` syntax incompatible with Python 3.14 → using classic `Column()` style
- `phonenumbers.E164_E.164` doesn't exist → use `phonenumbers.PhoneNumberFormat.E164`
- `telegram.constants.ReplyMarkup` removed → removed unused import
- `CallbackQueryHandler` from `telegram` (not `telegram.ext`) → use `telegram.ext.CallbackQueryHandler`
- `telegram.ext.persistence` module removed → removed persistence from app builder
- Bot name `relationship` conflicted with SQLAlchemy `relationship()` → renamed column to `relationship_`

## Pending / Not Done
- [ ] Real explainer video for landing page (replace YouTube embed placeholder)
- [ ] Web dashboard user detail pages
- [ ] User disable/delete from `/admin`
- [ ] PostgreSQL migration instructions
- [ ] Privacy policy page (needed for GDPR/NDPR)
- [ ] Terms of service
- [ ] Contact consent notification flow (send SMS to contact when added)
- [ ] Scheduled contact review reminders
- [ ] Multi-language (Hausa, Igbo, Yoruba)
- [ ] Deployment guide (Railway/Render)
