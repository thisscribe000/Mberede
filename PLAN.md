# Mberede — Emergency Contact Access via Telegram Bot

> **"Reach your loved ones when it matters most."**

---

## 1. Project Overview

### Core Concept
A Telegram bot that allows users to register emergency contacts and retrieve them via a secret PIN if their phone is lost or stolen. A good Samaritan finding a stranger's device can message the bot, enter the owner's secret code, and get access to the right contacts — with the option to send an SOS alert as well.

### Problem Statement
- **Phone lost/stolen** → victim has zero contacts accessible
- **Stranded** → no way to reach family or friends
- **Emergency** → critical time lost trying to figure out what to do
- **No internet?** → SMS fallback ensures reachability

### Target Users
- General public (anyone with a phone at risk of loss/theft)
- Travelers abroad
- Vulnerable individuals (elderly, medical conditions)
- Organizations wanting to issue staff emergency access tools

---

## 2. Architecture

### Tech Stack
```
Language:        Python 3.11+
Telegram Bot:    python-telegram-bot (v20+)
Database:        SQLite (Phase 1) → PostgreSQL (Phase 2)
SMS:             Twilio / Africa's Talking
Auth:            bcrypt (PIN hashing) + Telegram User ID
Hosting:         Railway / Render / VPS
```

### Project Structure
```
mberede/
├── bot/
│   ├── __init__.py
│   ├── app.py              # Main bot entry point
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── start.py        # /start command
│   │   ├── register.py     # Registration flow
│   │   ├── emergency.py    # Emergency access flow
│   │   ├── contacts.py     # Contact management
│   │   ├── sos.py          # SOS alert flow
│   │   └── admin.py        # Admin/debug commands
│   ├── keyboards/
│   │   ├── __init__.py
│   │   └── reply.py        # Reply keyboards
│   └── utils/
│       ├── __init__.py
│       ├── auth.py         # PIN verification
│       ├── rate.py         # Rate limiting
│       └── validators.py   # Input validation
├── core/
│   ├── __init__.py
│   ├── database.py         # DB connection & models
│   ├── models.py           # SQLAlchemy models
│   ├── sms.py             # SMS service abstraction
│   └── config.py          # Environment config
├── migrations/
├── tests/
│   ├── __init__.py
│   ├── test_auth.py
│   ├── test_bot_handlers.py
│   └── test_db.py
├── .env.example
├── .gitignore
├── requirements.txt
├── main.py                 # Gunicorn entry point
└── README.md
```

### Database Schema

#### Table: `users`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| telegram_user_id | BIGINT | Telegram user ID (unique) |
| telegram_username | VARCHAR(255) | Telegram username |
| pin_hash | VARCHAR(255) | bcrypt hash of PIN |
| is_active | BOOLEAN | Account active status |
| silent_mode | BOOLEAN | Hide bot responses (panic mode) |
| created_at | TIMESTAMP | |
| updated_at | TIMESTAMP | |
| last_accessed_at | TIMESTAMP | |
| failed_attempts | INT | Brute-force tracking |
| locked_until | TIMESTAMP | Account lockout time |

#### Table: `emergency_contacts`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK to users |
| name | VARCHAR(255) | Contact name |
| phone | VARCHAR(20) | Phone number (E.164) |
| relationship | VARCHAR(100) | e.g. "Spouse", "Parent" |
| priority | INT | Order of contacts (1 = highest) |
| is_verified | BOOLEAN | SMS verification done |
| created_at | TIMESTAMP | |

#### Table: `access_logs`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK to users |
| accessor_telegram_id | BIGINT | Who accessed |
| action | VARCHAR(50) | e.g. "viewed_contact", "sos_sent" |
| contact_id | UUID | FK to emergency_contacts (nullable) |
| ip_address | VARCHAR(45) | Accessor's IP |
| timestamp | TIMESTAMP | |
| success | BOOLEAN | |

#### Table: `sos_logs`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK to users |
| contact_id | UUID | FK to emergency_contacts |
| message | TEXT | Custom SOS message |
| sent_at | TIMESTAMP | |
| delivered | BOOLEAN | SMS delivery status |
| twilio_sid | VARCHAR(255) | SMS provider message ID |

#### Table: `recovery_codes`
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | FK to users |
| code | VARCHAR(8) | One-time recovery code |
| used | BOOLEAN | Whether it's been used |
| expires_at | TIMESTAMP | |
| created_at | TIMESTAMP | |

---

## 3. User Flows

### Flow 1: Registration (First-Time Setup)

```
User                          Bot
  |                            |
  |---- /start --------------->|
  |                            |
  |<--- "Welcome to Mberede" --|
  |<--- "Create a secret PIN" -|
  |                            |
  |---- (enters 4-6 digit) --->|
  |                            |
  |<--- "Confirm your PIN" -----|
  |                            |
  |---- (re-enters PIN) ------>|
  |                            |
  |<--- "PIN set! Now add" ----|
  |<--- "your first contact" --|
  |                            |
  |---- "John Doe" ------------>|
  |                            |
  |<--- "Enter John's number" -|
  |                            |
  |---- "+2348012345678" ------>|
  |                            |
  |<--- "Relationship?" -------|
  |<--- [Inline: Spouse|Parent|]|
  |<--- [Sibling|Friend|Other] |
  |                            |
  |<--- "Contact saved!" ------|
  |<--- [+ Add Another] -------|
  |<--- [I'm done] ------------|
  |                            |
  |<--- "You're all set!" -----|
  |<--- [View Contacts] -------|
  |<--- [Manage Contacts] -----|
```

### Flow 2: Emergency Access (Stranger Finds Device)

```
Stranger (on borrowed/found device)
  |
  |---- /start --------------->|
  |                            |
  |<--- "Hi! If you found a" --|
  |<--- "device, enter the" ---|
  |<--- "owner's secret code" -|
  |                            |
  |---- "1234" ---------------->|
  |                            |
  |<--- [Select Contact] ------|
  |<--- 1. Jane Doe (Wife) ----|
  |<--- 2. Dr. Smith (Doc) ----|
  |                            |
  |---- "1" ------------------>|
  |                            |
  |<--- "Jane Doe: +234..." ---|
  |<--- [Call] [SMS] [SMS SOS]|
  |                            |
  |---- "SMS SOS" ------------->|
  |                            |
  |<--- "SOS sent! Jane has" --|
  |<--- "been notified." ------|
```

### Flow 3: SOS Alert (From Owner's Device — if recovered or secondary device)

```
User                          Bot
  |                            |
  |---- /sos ----------------->|
  |                            |
  |<--- "Verify with PIN" -----|
  |                            |
  |---- "1234" ---------------->|
  |                            |
  |<--- "Send SOS to:" ---------|
  |<--- 1. Jane Doe (Wife) ----|
  |<--- 2. Dr. Smith (Doc) ----|
  |                            |
  |---- "1,2" ---------------->|
  |                            |
  |<--- "Sending SOS to 2" ----|
  |<--- "contacts..." ---------|
  |                            |
  |<--- "Jane notified ✓" ------|
  |<--- "Dr. Smith notified ✓"--|
```

---

## 4. Bot Commands

| Command | Description | Auth Required |
|---------|-------------|--------------|
| `/start` | Main entry point — detect existing user | No |
| `/register` | Start registration flow | No |
| `/myid` | Get your Telegram user ID | No |
| `/emergency` | Begin emergency access flow | No |
| `/sos` | Trigger SOS alert to contacts | Yes (PIN) |
| `/contacts` | View all your emergency contacts | Yes (PIN) |
| `/add` | Add a new emergency contact | Yes (PIN) |
| `/remove <name>` | Remove an emergency contact | Yes (PIN) |
| `/silent` | Toggle silent/panic mode | Yes (PIN) |
| `/panic` | Silent SOS — no bot response visible | Yes (PIN) |
| `/recover` | Start account recovery flow | No |
| `/help` | Show help information | No |
| `/settings` | Manage account settings | Yes (PIN) |
| `/export` | Export your data (GDPR) | Yes (PIN) |
| `/delete` | Delete your account and data | Yes (PIN) |

---

## 5. Feature Tiers

### Phase 1 — MVP (Core, Build First)
- [ ] Telegram bot with registration flow
- [ ] 4-6 digit PIN setup with bcrypt hashing
- [ ] Add/view up to 5 emergency contacts
- [ ] Emergency access via PIN
- [ ] SMS SOS alerts via Twilio/Africa's Talking
- [ ] Rate limiting (5 failed PIN attempts = 15min lockout)
- [ ] Access logging for audit
- [ ] `silent_mode` toggle
- [ ] `.env` config management
- [ ] SQLite database
- [ ] Basic unit tests

### Phase 2 — Enhanced
- [ ] PostgreSQL migration with proper backups
- [ ] Temporary emergency codes (one-time use, expire in 24h)
- [ ] Location sharing with SOS
- [ ] Web dashboard for contact management
- [ ] Contact SMS verification
- [ ] Recovery codes (one-time backup codes)
- [ ] Telegram inline keyboard UI throughout
- [ ] Multi-language support (EN, HA, IG, YR)
- [ ] `panic` command — zero visible output
- [ ] Email fallback notifications to contacts

### Phase 3 — Advanced
- [ ] Medical ID storage (blood type, allergies, conditions)
- [ ] Trusted device whitelist
- [ ] Group notification to all contacts
- [ ] Offline-first mode: pre-generated QR code with embedded credentials
- [ ] Apple/Google device integration hints
- [ ] Scheduled contact review reminders
- [ ] Accessibility features (voice input, large text mode)
- [ ] Admin panel for support staff
- [ ] Analytics dashboard

### Future Brainstorm (Consider for Later)
- Voice message input for emergency contacts
- Wi-Fi QR code sharing (device-to-device, no internet)
- Integration with church/group directories
- Panic button hardware integration
- Insurance company integration
- Crowdsourced safety maps

---

## 6. Offline & Connectivity Strategy

### The Core Challenge
Telegram requires internet. But the whole point is emergency situations where connectivity may be limited.

### Scenario Analysis

| Scenario | Connectivity Available? | Solution |
|----------|------------------------|----------|
| Phone stolen, victim has laptop at home | Yes (laptop) | Telegram bot works |
| Phone stolen, victim finds café with WiFi | Yes (borrowed device) | Telegram bot works |
| Phone stolen, victim on road with no internet | Unlikely | SMS fallback needed |
| Finders use device they already own | Yes | Telegram bot works |
| Telegram blocked in country (e.g. China) | Possible | SMS + alternative bot (e.g. WhatsApp) |

### Strategies

#### Strategy 1: SMS Gateway (Primary Offline Fallback)
- Server sends SMS to emergency contacts on behalf of user
- **No internet needed on victim's side** — only on server
- Cost: ~$0.05–$0.08 per SMS (Twilio/Africa's Talking)
- Triggered via: Telegram bot (online) OR SMS command to server number
- SMS command: Send `SOS PIN CODE` to server number from any phone

#### Strategy 2: Pre-generated Offline Codes
- User generates printable QR codes / paper cards with:
  - Encrypted contact list
  - One-time use access codes
  - Server verification URL (optional, can be checked online)
- Good Samaritan scans or enters code
- Works WITHOUT any connectivity

#### Strategy 3: SMS-to-Telegram Bridge
- User sends SMS to a special number
- Server receives and forwards to Telegram bot
- Allows user to interact with bot via SMS only
- Complicated but powerful fallback

### Recommended Offline Approach
1. **Primary**: Telegram bot (online access)
2. **Fallback**: SMS from server to contacts (victim sends SMS command to bot number or dedicated number)
3. **Paper backup**: Generate printable emergency card with encrypted data

---

## 7. Things You May Not Have Considered

### Security Risks
- **Brute-force PIN attack**: 6 digits = only 1 million combinations. Rate limiting, lockouts, progressive delays.
- **PIN shoulder surfing**: The person who stole the phone might try to enter the PIN. Need silent mode / panic mode.
- **Contact consent**: Are your emergency contacts consenting to being stored and contacted in emergencies? Add a verification step.
- **PIN stored in plaintext on device**: If victim had PIN saved on phone notes, thief has it. Don't rely on PIN alone — consider trusted device approach.
- **Eavesdropping on Telegram**: Messages between bot and user could be intercepted on shared devices. Consider E2E encryption for sensitive flows.
- **SIM swap attacks**: Attacker social-engineers carrier to get new SIM with same number. Use Telegram User ID as primary auth, not phone number.
- **SQL injection via contact names**: Sanitize all input.
- **Bot token exposure**: Never commit `.env` files. Use secrets management.

### Privacy & Legal
- **GDPR / NDPR (Nigeria)**: Users must consent to data storage, have right to deletion (`/delete` command), right to export (`/export`). You need a privacy policy.
- **Contact consent**: Store a consent timestamp for each emergency contact.
- **Access logs are sensitive**: They reveal when someone tried to access a device. Who owns this data?
- **Data retention**: Auto-delete logs after 90 days?
- **Cross-border data**: If hosting in one country but users in another, which privacy laws apply?

### Operational Concerns
- **SMS costs**: Every SOS = money spent. How do you fund this? Freemium model? Donor-funded? Self-sustaining?
- **Telegram Bot API limits**: Max 30 messages per second. Bulk SOS to 5 contacts is fine, but scaling?
- **Phone number format**: International numbers are tricky. Always validate E.164 format. Store raw, display formatted.
- **Telegram username changes**: User changes their @username — your lookup by username breaks. Use Telegram User ID (stable) not username.
- **Bot blocking**: If too many people block the bot after SOS spam, Telegram may limit it.
- **Timezone handling**: SOS messages sent at 3 AM — maybe add quiet hours?
- **Multi-device access**: What if the owner and a stranger both try to access at the same time? Need session management.

### UX Edge Cases
- **What if user forgets PIN?** → Recovery flow with recovery codes or email verification
- **What if contact's phone is off?** → SMS queued, with delivery status
- **What if user adds the same contact twice?** → Dedupe by phone number
- **What if the contact says "stop texting me"?** → Need unsubscribe mechanism for contacts
- **What if user is under duress?** → Panic command with fake "all done" response
- **What if victim's number is also stolen?** → Can't SMS them, only Telegram fallback
- **What if the bot is used for harassment?** → Rate limiting + access logging + admin review
- **What if contact has a landline?** → SMS to landline may not work. Need call fallback?
- **What if the person can't read?** → Voice note support for contacts

### Infrastructure
- **Database backups**: What if server crashes? Lose all user data? Daily automated backups.
- **Bot token rotation**: What if token is compromised? Need a plan to rotate without downtime.
- **Hosting region**: Low latency matters. Users in Nigeria + hosting in US = slow. Consider Africa-based hosting (e.g. AWS Cape Town, or Railway/Render with EU or Africa regions).
- **SSL certificates**: For web dashboard. Let's Encrypt.
- **Monitoring**: What if bot goes down? Need health checks, alerts.
- **Graceful shutdown**: SIGTERM handling for clean bot shutdown.
- **Migration strategy**: How to migrate SQLite → PostgreSQL without data loss?

### UX Flow Improvements
- **Welcome screen** with quick actions (Register, Emergency, Help)
- **Progress indicators** for multi-step flows (Step 2 of 4)
- **Undo support** for accidental contact deletion
- **Time-to-live for sessions**: PIN confirmation expires after 10 minutes of inactivity
- **Confirmation dialogs** for destructive actions (delete contact, delete account)

---

## 8. Security Model

### PIN Security
```
PIN Storage:       bcrypt(pin, rounds=12) — NEVER store raw
PIN Verification:  Constant-time comparison (hmac.compare_digest)
Rate Limiting:     5 failed attempts → 15min lockout
                  10 failed attempts → 1hr lockout
                  20 failed attempts → account flagged for review
Progressive Delay: Each failed attempt adds 2s delay before next try
```

### Session Management
```
Session Token:    UUID v4, stored in DB, 10-minute TTL
Session Scope:   One active session per user at a time
Session Invalidation: On logout, password change, or 5 failed auth attempts
```

### Data Security
```
At Rest:       SQLite with journaling; PostgreSQL with encryption at rest (Phase 2)
In Transit:    HTTPS only (never allow HTTP)
Logs:           Hash Telegram user IDs in logs for privacy
Sensitive Ops:  PIN entry always masked
```

---

## 9. SMS Integration (Africa's Talking + Twilio)

### Africa's Talking (Recommended for Africa)
- Local coverage in 34 African countries
- Nigeria: ₦2-5 per SMS
- Registration: https://africastalking.com
- Python SDK: `africastalking`

### Twilio (Global + Reliable)
- Global coverage
- ~$0.05-0.08 per SMS
- Python SDK: `twilio`
- Pros: Very reliable, good webhooks
- Cons: More expensive than Africa's Talking for Africa

### SMS Flow
```
User triggers SOS
  → Server validates session
  → Server calls SMS provider API
  → SMS sent to all selected contacts
  → Delivery status webhook → update sos_logs.delivered
  → Telegram confirmation to user
```

---

## 10. Implementation Phases

### Phase 1: Foundation (Week 1-2)
- [ ] Project scaffold + virtual environment
- [ ] Environment config (python-dotenv)
- [ ] Database models + SQLite setup
- [ ] Telegram bot basic structure
- [ ] `/start` + `/help` commands
- [ ] User registration flow (telegram user id capture)
- [ ] PIN setup + hashing
- [ ] Contact CRUD operations
- [ ] Emergency access flow
- [ ] Rate limiting middleware
- [ ] Basic unit tests
- [ ] README + deployment instructions

### Phase 2: Communication (Week 3)
- [ ] SMS integration (Africa's Talking)
- [ ] SOS alert system
- [ ] Access logging
- [ ] Delivery status tracking
- [ ] Silent mode + panic mode
- [ ] Error handling + graceful degradation
- [ ] Session management
- [ ] Recovery code system

### Phase 3: Polish (Week 4)
- [ ] PostgreSQL migration
- [ ] Production deployment
- [ ] Monitoring setup
- [ ] Backup strategy
- [ ] Admin commands
- [ ] Data export (GDPR)
- [ ] Account deletion flow
- [ ] End-to-end tests
- [ ] Privacy policy + terms of service

### Phase 4: Enhancement (Week 5-6)
- [ ] Web dashboard
- [ ] Location sharing with SOS
- [ ] Multi-language support
- [ ] Recovery codes
- [ ] Contact SMS verification

---

## 11. Cost Estimation (Monthly)

| Item | Cost |
|------|------|
| Hosting (Railway/Render) | $0-5 (free tiers available) |
| SMS via Africa's Talking | ~$0.50 per 100 SOS events |
| SMS via Twilio (fallback) | ~$1.00 per 200 SMS |
| Domain (optional) | $10-15/year |
| Database backups | $0 (built into hosting) |
| **Total MVP** | **~$0-5/month** |

---

## 12. Key Files to Create

1. `requirements.txt`
2. `.env.example`
3. `core/config.py`
4. `core/database.py`
5. `core/models.py`
6. `core/sms.py`
7. `bot/app.py`
8. `bot/handlers/start.py`
9. `bot/handlers/register.py`
10. `bot/handlers/emergency.py`
11. `bot/handlers/sos.py`
12. `bot/handlers/contacts.py`
13. `bot/utils/auth.py`
14. `bot/utils/rate.py`
15. `bot/utils/validators.py`
16. `bot/keyboards/reply.py`
17. `main.py`
18. `tests/test_auth.py`
19. `tests/test_bot_handlers.py`
20. `README.md`

---

## 13. Open Questions for You to Decide

1. **SMS provider**: Africa's Talking (cheaper for Africa) or Twilio (global)?
2. **Funding model**: Free for all? Freemium? Donations? Organization sponsorship?
3. **Hosting**: Railway (easy), Render, or self-hosted VPS?
4. **Database**: Start with SQLite or go straight to PostgreSQL?
5. **Privacy policy**: Will you publish one? Needed for GDPR/NDPR compliance.
6. **Target geography**: Primarily Nigeria? Pan-Africa? Global?
7. **Branding**: "Mberede" — does it have a specific meaning? Should we build cultural context into the UI?
8. **Emergency message template**: Default SOS message — what should it say?
9. **Contact limit**: 5 contacts per user in MVP? More?
10. **Data retention**: How long to keep access logs? 30, 60, or 90 days?
