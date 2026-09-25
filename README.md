# 🤖 Couple Bot — Telegram

<p align="center">
  <b>English</b> •
  <a href="README.pt-BR.md">Português (Brasil)</a>
</p>

---

A virtual assistant for Telegram designed to help couples seamlessly organize shared routines, appointments, and important dates with smart automated notifications and real-time syncing.

---

## 🚀 Key Features

- 💑 **Secure Couple Pairing:** Connect partners using a temporary invite code (`CASAL-XXXX`) with a 30-minute expiration and mutual notification.
- 📅 **Guided Event Creation:**
  - Step-by-step interactive flow: Title, date (`DD/MM/YYYY`), and time (`HH:MM`) with past date validation;
  - Flexible participant scope: **Personal** (`👤 Me`), **Partner** (`👩 Her / 👨 Him`), or **Shared** (`❤️ Both of us`);
  - Recurrence rules: Daily, Weekly, Monthly, and Yearly;
  - Configurable advance reminders (10m, 30m, 1h, 1 day before).
- 🔍 **Quick & Organized Queries:**
  - `/hoje` — View today's schedule visually grouped by participant;
  - `/semana` — 7-day projection displaying upcoming events and free days;
  - `/eventos` — Chronological list of all upcoming active events.
- 🗑️ **Safe Event Deletion:**
  - `/delete` — Interactive list with a confirmation dialog before permanent deletion;
  - Automatic notification to partner upon cancellation of shared events;
  - Cascading cleanup of pending reminders from the scheduler queue.
- ⏰ **Automated Notification System:**
  - Direct Telegram notifications dispatched at the exact scheduled reminder time;
  - Inline action buttons: acknowledge (`[✓ OK]`) or snooze alarm (`[⏰ Snooze]`: 10m, 30m, 1h).

---

## 🛠️ Tech Stack

- **Language:** Python 3.12+
- **Telegram Framework:** `python-telegram-bot` (v22+) with integrated `JobQueue` (APScheduler)
- **Database & ORM:** `SQLAlchemy` 2.0+ with seamless support for **PostgreSQL** (production via Supabase) and **SQLite** (local development)
- **Database Driver:** `psycopg2-binary`
- **Timezone Management:** `pytz` (default: `America/Sao_Paulo`)
- **Automated Testing:** `pytest` + `anyio` (30 test cases covering handlers, services, database isolation, and security)

---

## 📂 Project Structure

```text
bot_telegram/
├── app/
│   ├── bot/
│   │   ├── handlers/         # Command, query, and conversation handlers
│   │   ├── keyboards/        # Inline keyboards and navigation menus
│   │   └── states/           # Conversation state enumerations
│   ├── database/
│   │   ├── database.py       # Engine initialization and session factory
│   │   ├── models.py         # SQLAlchemy data models (User, Couple, Event, Reminder)
│   │   └── repositories/     # Decoupled database CRUD operations
│   ├── scheduler/
│   │   └── scheduler.py      # Background worker for reminder dispatch & snoozing
│   ├── services/             # Business logic & recurrence computation
│   ├── utils/                # Date/time utilities and timezone conversions
│   └── config.py             # Environment configuration & validation
├── tests/                    # Automated test suite
├── .env.example              # Sample environment configuration
├── .gitignore                # Git ignore rules for secrets and caches
├── requirements.txt          # Python dependencies
├── main.py                   # Application entrypoint
├── README.md                 # English documentation
└── README.pt-BR.md           # Portuguese documentation
```

---

## ⚙️ Local Installation & Setup

### 1. Prerequisites
- Python 3.12 or newer installed;
- A Telegram account.

### 2. Creating your Telegram Bot
1. Open Telegram and start a chat with [@BotFather](https://t.me/BotFather);
2. Send `/newbot`;
3. Pick a display name and username (must end in `bot`);
4. Copy the generated HTTP API token.

### 3. Clone & Environment Setup
```bash
# Clone the repository
git clone https://github.com/dougbrunos/bot_casal.git
cd bot_casal

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy the example template:
```bash
cp .env.example .env
```

Edit `.env` with your credentials:
```env
TELEGRAM_BOT_TOKEN=your_token_from_botfather
DATABASE_URL=sqlite:///data/app.db
TIMEZONE=America/Sao_Paulo
```

> **For Supabase / PostgreSQL:** Replace `DATABASE_URL` with your connection string:
> ```env
> DATABASE_URL=postgresql://postgres.[REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
> ```

### 5. Run the Bot
With your virtual environment active:
```bash
python main.py
```

The application will start long polling and register background reminder jobs. Open your bot in Telegram and send `/start` to begin!

---

## ☁️ Free Cloud Deployment (24/7 with Render & Supabase)

You can host this bot completely free (R$ 0 / $0) using **Supabase** + **Render**:

### 1. Database (Supabase - Free PostgreSQL)
1. Sign up at [supabase.com](https://supabase.com) and create a project;
2. In **Project Settings** > **Database**, copy the **URI** connection string;
3. Database tables are generated automatically when the bot runs for the first time.

### 2. Application Hosting (Render - Free)
1. Sign up at [render.com](https://render.com) and link your GitHub repository;
2. Create a new **Web Service** (or **Background Worker**):
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
3. Under **Environment Variables**, set the values from your `.env`:
   - `TELEGRAM_BOT_TOKEN`
   - `DATABASE_URL`
   - `TIMEZONE`
4. Deploy! Render will keep the bot running and checking reminders 24/7.

---

## 🧪 Running Automated Tests

To execute the test suite:
```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## 📖 Telegram Commands

| Command | Description |
|---|---|
| `/start` | Starts the bot, registers the user, and opens the main menu |
| `/menu` | Opens the couple navigation shortcuts menu |
| `/ajuda` or `/help` | Displays help guide and command usage |
| `/add` | Starts guided flow to create a new appointment |
| `/hoje` | Displays today's schedule grouped by participant |
| `/semana` | Displays the next 7 days projection |
| `/eventos` | Lists upcoming appointments in chronological order |
| `/delete` | Interactive menu to cancel/delete appointments |
| `/cancelar` | Cancels any ongoing interactive conversation |

---

## 📄 License

This project is licensed under the MIT License. Feel free to use, modify, and distribute.
