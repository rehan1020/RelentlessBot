from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from src.database.models import upsert_user
from src.config import settings

router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    user = message.from_user
    if user:
        await upsert_user(
            user_id=user.id,
            chat_id=message.chat.id,
            username=user.username,
            first_name=user.first_name
        )

    welcome_text = (
        "👋 <b>Welcome to RelentlessBot!</b>\n\n"
        "I am your personal accountability partner. I make sure your daily to-do items "
        "actually get completed by checking in and reminding you continuously until you mark them done.\n\n"
        "⚡ <b>How it works:</b>\n"
        "1. <b>Send your tasks anytime:</b>\n"
        "   Separate by newlines or commas.\n"
        "2. <b>Set priority:</b>\n"
        "   Tap 🔴 High (45m), 🟡 Medium (1.5h), or 🟢 Low (2.5h).\n"
        "3. <b>Relentless Nudges:</b>\n"
        "   No snooze buttons. I will keep reminding you until you tap [✅ Done].\n"
        "4. <b>Quiet Hours:</b>\n"
        f"   Completely silent between <code>{settings.quiet_hours_start}</code> and <code>{settings.quiet_hours_end}</code>.\n\n"
        "📌 <b>Commands:</b>\n"
        "• /tasks or /list — View pending tasks\n"
        "• /clear — Reset or clear tasks\n"
        "• /help — Full usage instructions\n\n"
        "👉 <i>Send me your to-do list right now to get started!</i>"
    )
    await message.answer(welcome_text, parse_mode="HTML")

@router.message(Command("help"))
async def handle_help(message: Message):
    help_text = (
        "📖 <b>RelentlessBot Help & Usage</b>\n\n"
        "<b>Adding Tasks:</b>\n"
        "Simply send a message with your tasks. You can use:\n"
        "• <b>Newlines:</b>\n"
        "  Fix deployment bug\n"
        "  Respond to client\n"
        "  Go to gym\n\n"
        "• <b>Commas:</b>\n"
        "  Fix deployment bug, Respond to client, Go to gym\n\n"
        "• <b>Bullets or numbers:</b>\n"
        "  1. Fix deployment bug\n"
        "  - Respond to client\n\n"
        "<b>Priority & Frequencies:</b>\n"
        f"• 🔴 <b>High:</b> Every {settings.high_priority_interval_minutes} minutes\n"
        f"• 🟡 <b>Medium:</b> Every {settings.medium_priority_interval_minutes} minutes\n"
        f"• 🟢 <b>Low:</b> Every {settings.low_priority_interval_minutes} minutes\n\n"
        "<b>Commands:</b>\n"
        "• /tasks — List all pending tasks\n"
        "• /clear — Clear tasks\n"
        "• /start — Restart or show welcome info"
    )
    await message.answer(help_text, parse_mode="HTML")
