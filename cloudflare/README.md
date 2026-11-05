# ☁️ RelentlessBot on Cloudflare Free Tier

Host **RelentlessBot 24/7 forever at zero cost** on Cloudflare Workers and Cloudflare D1 (Serverless SQLite).

No VPS, no home server, and no credit card required.

---

## ⚡ Architecture

- **Runtime**: Cloudflare Workers (V8 Edge)
- **Database**: Cloudflare D1 (Serverless SQLite at edge)
- **Framework**: [grammY](https://grammy.dev/)
- **Scheduler**: Cloudflare Cron Triggers (`* * * * *` - checks every minute)
- **Ingestion**: Telegram Webhooks (instant event push)

---

## 🚀 5-Minute Setup Guide

### 1. Prerequisites
- A free account on [Cloudflare](https://dash.cloudflare.com/sign-up).
- Node.js 18+ installed on your computer.
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather).

### 2. Install Dependencies
Open your terminal in the `cloudflare/` directory:
```bash
npm install
```

### 3. Log into Cloudflare
```bash
npx wrangler login
```
*(This will open a browser window to authenticate with your Cloudflare account).*

### 4. Create your Cloudflare D1 Database
Run:
```bash
npx wrangler d1 create relentless-db
```
Wrangler will output something like:
```toml
[[d1_databases]]
binding = "DB"
database_name = "relentless-db"
database_id = "xxxx-xxxx-xxxx-xxxx"
```
Copy that `database_id` and paste it into `cloudflare/wrangler.toml`.

### 5. Initialize the Database Schema
Execute the schema to create the `users` and `tasks` tables:
```bash
npx wrangler d1 execute relentless-db --file=./schema.sql
```

### 6. Set Your Telegram Bot Token Secret
```bash
npx wrangler secret put BOT_TOKEN
```
Paste your Bot Token when prompted.

*(Optional)* If you want to restrict the bot to your Telegram User ID only, set `ALLOWED_USER_IDS` in `wrangler.toml`.

### 7. Deploy to Cloudflare!
```bash
npx wrangler deploy
```
Wrangler will print your live worker URL:
```text
https://relentless-bot.<your-subdomain>.workers.dev
```

### 8. One-Click Webhook Registration
Open this URL in your web browser:
```text
https://relentless-bot.<your-subdomain>.workers.dev/set-webhook
```
You will see:
> **✅ Webhook Successfully Registered!**

That's it! Your bot is live **24/7 forever**! Open Telegram and send `/start` or paste your tasks.

---

## ⚙️ Configuration Reference (`wrangler.toml`)

| Setting | Default | Description |
| :--- | :--- | :--- |
| `TIMEZONE` | `Asia/Kolkata` | Timezone string for quiet hours & morning reminders |
| `QUIET_HOURS_START` | `00:00` | Start of quiet hours (Midnight) |
| `QUIET_HOURS_END` | `07:00` | End of quiet hours (7:00 AM) |
| `MORNING_PROMPT_TIME`| `07:05` | Time when morning greeting & uncompleted tasks are sent |
| `HIGH_PRIORITY_INTERVAL_MINUTES` | `45` | High priority reminder frequency |
| `MEDIUM_PRIORITY_INTERVAL_MINUTES` | `90` | Medium priority reminder frequency |
| `LOW_PRIORITY_INTERVAL_MINUTES` | `150`| Low priority reminder frequency |
| `ALLOWED_USER_IDS` | `""` | Comma-separated user IDs allowed to interact |
