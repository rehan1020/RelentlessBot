<div align="center">

# ⚡ RelentlessBot

**A self-hosted Telegram accountability bot that nags you until your daily tasks are actually completed.**  
*Zero friction. No snoozing. Relentless execution.*

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-v3-2CA5E0?logo=telegram&logoColor=white)](https://docs.aiogram.dev/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

[Features](#-key-features) • [Quick Start](#-quick-start) • [Docker Deployment](#-docker-deployment) • [Configuration](#-configuration) • [Daily Lifecycle](#-daily-lifecycle) • [Contributing](#-contributing)

</div>

---

## 🎯 Why RelentlessBot?

Most to-do apps fail because they rely on you remembering to open them. **RelentlessBot reaches out to you where you already spend your time—on Telegram.**

Unlike traditional reminder apps that let you hit "Snooze" until tomorrow, **RelentlessBot has no snooze button**. Once a task enters your daily queue, it will continuously check in on you at an interval matching the task's importance until you either mark it **[ ✅ Done ]** or consciously **[ ❌ Drop ]** it.

---

## ✨ Key Features

- 📥 **Zero-Friction Ingestion**: Send tasks line-by-line or separated by commas. Paste anytime, whether morning or mid-day.
- 🔴🟡🟢 **Interactive Priority Setup**: 1-tap Telegram inline buttons to calibrate reminder frequency for every task.
- ⏰ **Dynamic Reminder Cadence**:
  - **🔴 High Priority**: Reminds every **45 minutes** (for crucial blockers & deadlines).
  - **🟡 Medium Priority**: Reminds every **90 minutes (1.5h)** (for normal daily goals).
  - **🟢 Low Priority**: Reminds every **150 minutes (2.5h)** (for routine errands).
- 🚫 **No Snooze Policy**: No excuses. The bot checks in persistently until the task is finished.
- 🌙 **Quiet Hours (12:00 AM – 7:00 AM)**: Completely silent during sleep hours. Pending reminders resume right at the start of your day.
- ☀️ **Morning Kickoff (7:05 AM)**: Wakes up, prompts you for today's to-do items, and offers to keep or clear yesterday's unfinished items.
- 🔒 **Private & Secure**: Built-in `ALLOWED_USER_IDS` whitelist prevents strangers from messaging or consuming your bot.
- 🛡️ **Crash-Proof & Lightweight**: Powered by SQLite in **WAL mode (Write-Ahead Logging)**; runs seamlessly on a tiny VPS or Raspberry Pi (<50MB RAM).

---

## 🔄 Daily Lifecycle

```mermaid
flowchart TD
    A[07:05 AM: Morning Wake-up] --> B[Bot prompts for daily to-dos + reviews unfinished tasks]
    B --> C[User sends tasks via newlines or commas]
    C --> D[Bot prompts priority for each task via inline buttons]
    D --> E[Tasks scheduled into reminder loop]
    E --> F{Task completed?}
    F -- Yes --> G[Tap Done: Task recorded & reminder stopped]
    F -- No --> H{Inside Quiet Hours 00:00 - 07:00?}
    H -- Yes --> I[Silent: Hold reminders until morning]
    H -- No --> J[Relentless Nudge sent with Done & Drop buttons]
    J --> E
```

---

## 🚀 Quick Start

### 1. Get Telegram Bot Credentials
1. Open Telegram and search for [@BotFather](https://t.me/BotFather).
2. Send `/newbot`, name your bot, and copy your **Bot Token**.
3. (Recommended) Get your numerical Telegram User ID from [@userinfobot](https://t.me/userinfobot) to restrict access to yourself.

### 2. Clone Repository
```bash
git clone https://github.com/rehan1020/RelentlessBot.git
cd RelentlessBot
```

### 3. Configure Environment
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Open `.env` and fill in:
```env
BOT_TOKEN=123456789:ABCDefghIJKlmnoPQRstuv-WXYZ
ALLOWED_USER_IDS=your_telegram_user_id
TIMEZONE=Asia/Kolkata
```

---

## 🐳 Docker Deployment (Recommended)

Run 24/7 on your home server, VPS, or Raspberry Pi with a single command:

```bash
docker compose up -d
```

To view logs:
```bash
docker compose logs -f
```

To stop:
```bash
docker compose down
```

---

## 💻 Local Setup (Python 3.11+)

```bash
# 1. Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the bot
python main.py
```

---

## ⚙️ Configuration Reference

All settings can be customized in `.env`:

| Variable | Default | Description |
| :--- | :--- | :--- |
| `BOT_TOKEN` | *Required* | Telegram API token from @BotFather |
| `ALLOWED_USER_IDS` | `""` | Comma-separated user IDs allowed to interact. If empty, anyone can use it. |
| `TIMEZONE` | `Asia/Kolkata` | Your timezone (e.g., `UTC`, `America/New_York`, `Europe/London`). |
| `QUIET_HOURS_START` | `00:00` | 24-hr time when reminders pause (Midnight). |
| `QUIET_HOURS_END` | `07:00` | 24-hr time when reminders resume (7:00 AM). |
| `MORNING_PROMPT_TIME` | `07:05` | Time when bot asks for today's new task list. |
| `HIGH_PRIORITY_INTERVAL_MINUTES` | `45` | Interval for High priority tasks. |
| `MEDIUM_PRIORITY_INTERVAL_MINUTES` | `90` | Interval for Medium priority tasks (1.5h). |
| `LOW_PRIORITY_INTERVAL_MINUTES` | `150` | Interval for Low priority tasks (2.5h). |
| `DB_PATH` | `data/relentless.db`| SQLite database file location. |

---

## 🎮 How to Use

### Adding Tasks Anytime
Send a message in any of these formats:

**Newline format:**
```text
Deploy staging backend
Draft API documentation
Order gym supplements
```

**Comma-separated format:**
```text
Deploy staging backend, Draft API documentation, Order gym supplements
```

**Numbered / Bullet format:**
```text
1. Deploy staging backend
2. Draft API documentation
- Order gym supplements
```

RelentlessBot will immediately prompt you with inline buttons to assign priorities.

### Bot Commands
- `/tasks` or `/list` — View active tasks grouped by priority with 1-tap complete buttons.
- `/clear` or `/reset` — Clear all pending tasks or wipe completed history.
- `/help` — Overview of syntax, intervals, and commands.
- `/start` — Welcome message and instructions.

---

## 🧪 Running Tests

The test suite validates parser edge cases, database persistence, and quiet-hours schedule calculations:

```bash
python -m unittest tests/test_core.py
```

---

## 🤝 Contributing

Contributions, feature ideas, and pull requests are warmly welcomed!
1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for details.

---

<div align="center">
Built with determination by <a href="https://github.com/rehan1020">rehan1020</a>.
</div>
