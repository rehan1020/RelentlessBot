import logging
from datetime import datetime, timedelta, time
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from src.config import settings
from src.database.models import (
    get_all_users,
    get_due_tasks,
    update_task_reminder,
    get_pending_tasks_for_user
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone=settings.tz)

def calculate_next_reminder_time(interval_minutes: int, from_time: Optional[datetime] = None) -> datetime:
    """
    Calculates the next reminder time based on interval.
    If the next reminder falls within quiet hours, pushes it to the end of quiet hours.
    """
    now = from_time or datetime.now(settings.tz)
    target = now + timedelta(minutes=interval_minutes)

    # Check if target falls in quiet hours
    if settings.is_in_quiet_hours(target):
        _, end_quiet = settings.get_quiet_time_range()
        # Find next occurrence of end_quiet
        candidate = target.replace(hour=end_quiet.hour, minute=end_quiet.minute, second=0, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        target = candidate

    return target

async def process_due_reminders(bot: Bot) -> None:
    """Background job checking for tasks that are due for a reminder."""
    # Never disturb during quiet hours
    if settings.is_in_quiet_hours():
        return

    now = datetime.now(settings.tz)
    now_iso = now.isoformat()

    try:
        due_tasks = await get_due_tasks(now_iso)
        for task in due_tasks:
            task_id = task["id"]
            chat_id = task["chat_id"]
            title = task["title"]
            priority = task["priority"] or "medium"
            remind_count = task["remind_count"] + 1

            p_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")

            text = (
                f"⏰ <b>Relentless Nudge #{remind_count}!</b>\n\n"
                f"{p_icon} <b>[{priority.upper()}]</b> {title}\n"
                f"Status: Incomplete\n\n"
                f"<i>No excuses. Mark it done once finished!</i>"
            )

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="✅ Done", callback_data=f"done:{task_id}"),
                        InlineKeyboardButton(text="❌ Drop", callback_data=f"drop:{task_id}")
                    ]
                ]
            )

            try:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                logger.error(f"Failed to send reminder for task {task_id} to chat {chat_id}: {e}")

            # Schedule next reminder
            interval = settings.get_interval_for_priority(priority)
            next_time = calculate_next_reminder_time(interval, from_time=now)
            await update_task_reminder(task_id, now_iso, next_time.isoformat())

    except Exception as e:
        logger.error(f"Error in process_due_reminders: {e}", exc_info=True)

async def send_morning_prompt(bot: Bot) -> None:
    """Sends morning prompt asking for today's tasks and listing any unfinished ones."""
    users = await get_all_users()
    for user in users:
        chat_id = user["chat_id"]
        user_id = user["user_id"]

        pending = await get_pending_tasks_for_user(user_id)
        
        msg = (
            "☀️ <b>Good morning! Time to conquer the day.</b>\n\n"
            "What is your to-do list for today?\n"
            "Send your tasks separated by <b>newlines</b> or <b>commas</b>.\n\n"
            "<i>Example:</i>\n"
            "• Fix auth bug\n"
            "• Call team lead\n"
            "• Go to gym"
        )

        if pending:
            task_list_str = "\n".join([f"• {t['title']} ({t['priority'] or 'no priority'})" for t in pending])
            msg += (
                f"\n\n📌 <b>You also have {len(pending)} unfinished task(s) from earlier:</b>\n"
                f"{task_list_str}"
            )
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(text="📋 Keep All", callback_data="keep_old_tasks"),
                        InlineKeyboardButton(text="🗑️ Clear Old Tasks", callback_data="clear_old_tasks")
                    ]
                ]
            )
        else:
            keyboard = None

        try:
            await bot.send_message(chat_id=chat_id, text=msg, reply_markup=keyboard, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Failed to send morning prompt to user {user_id}: {e}")

def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    """Configures and starts the background scheduler."""
    # 1. Periodic reminder checker (runs every 60 seconds)
    scheduler.add_job(
        process_due_reminders,
        "interval",
        seconds=60,
        args=[bot],
        id="reminder_checker",
        replace_existing=True
    )

    # 2. Daily morning prompt at MORNING_PROMPT_TIME
    m_hour, m_minute = map(int, settings.morning_prompt_time.split(":"))
    scheduler.add_job(
        send_morning_prompt,
        "cron",
        hour=m_hour,
        minute=m_minute,
        timezone=settings.tz,
        args=[bot],
        id="morning_prompt",
        replace_existing=True
    )

    return scheduler
