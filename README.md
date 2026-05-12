# Mberede — Emergency Contact Access via Telegram Bot

> **"Reach your loved ones when it matters most."**

A Telegram bot that allows users to register emergency contacts and retrieve them via a secret PIN if their phone is lost or stolen. Anyone who finds a lost device can message the bot, enter the owner's secret code, and access their emergency contacts.

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/thisscribe000/Mberede.git
cd Mberede
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `TELEGRAM_BOT_TOKEN` — Get from [@BotFather](https://t.me/BotFather)
- `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_PHONE_NUMBER` — Twilio credentials
- `SECRET_KEY` — Generate with `python -c "import secrets; print(secrets.token_hex(32))"`

### 3. Run

```bash
python main.py
```

### 4. Create Your Telegram Bot

1. Open [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Follow the prompts
4. Copy the bot token to `.env`

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome screen |
| `/register` | Set up your PIN and emergency contacts |
| `/emergency` | Access emergency contacts (for device finders) |
| `/sos` | Send SOS alert to your contacts |
| `/contacts` | View your emergency contacts |
| `/add` | Add a new contact |
| `/remove <name>` | Remove a contact |
| `/silent` | Toggle silent mode |
| `/delete <PIN>` | Delete your account |
| `/myid` | Get your Telegram user ID |
| `/help` | Show help |

## Architecture

```
mberede/
├── bot/
│   ├── app.py              # Main bot entry point
│   ├── handlers/           # Command handlers
│   ├── keyboards/          # Reply/inline keyboards
│   └── utils/              # Auth, validation, rate limiting
├── core/
│   ├── config.py           # Environment configuration
│   ├── models.py           # Database models
│   └── sms.py             # SMS provider abstraction
├── tests/                  # Unit tests
├── main.py                 # Gunicorn entry point
└── PLAN.md                 # Full project plan
```

## SMS Providers

Currently supported:
- **Twilio** (default) — Global coverage
- **Africa's Talking** — Cheaper for Africa

Set `SMS_PROVIDER=africas_talking` in `.env` for Africa's Talking.

## Security

- PINs are hashed with bcrypt (12 rounds)
- Rate limiting: 5 failed attempts = 15-minute lockout
- Constant-time PIN comparison
- All data in transit over HTTPS

## Deployment

### Railway

1. Connect your GitHub repo
2. Add environment variables
3. Set start command: `python main.py`

### Render

1. Create a new Web Service
2. Connect your GitHub repo
3. Add environment variables
4. Set start command: `python main.py`

## License

MIT
