from aiogram import Router, F
from aiogram.types import CallbackQuery
from datetime import datetime

from src.database.models import (
    set_task_priority,
    get_task_by_id,
    get_tasks_needing_priority,
    mark_task_completed,
    mark_task_dropped,
    clear_user_tasks,
    get_pending_tasks_for_user
)
from src.services.scheduler import calculate_next_reminder_time
from src.handlers.tasks import get_priority_keyboard
from src.config import settings

router = Router()

@router.callback_query(F.data.startswith("prio:"))
async def handle_priority_callback(callback: CallbackQuery):
    _, task_id_str, priority = callback.data.split(":")
    task_id = int(task_id_str)
    user_id = callback.from_user.id

    task = await get_task_by_id(task_id)
    if not task:
        await callback.answer("Task not found.", show_alert=True)
        return

    interval = settings.get_interval_for_priority(priority)
    next_time = calculate_next_reminder_time(interval)

    await set_task_priority(task_id, priority, next_time.isoformat())
    await callback.answer(f"Set to {priority.upper()} priority ({interval}m)")

    # Check if there are other tasks awaiting priority
    remaining = await get_tasks_needing_priority(user_id)
    if remaining:
        next_task = remaining[0]
        prompt_text = (
            f"✅ Saved priority for <i>\"{task['title']}\"</i>.\n\n"
            f"Next task <b>({len(remaining)} pending)</b>:\n"
            f"👉 <b>{next_task['title']}</b>\n\n"
            f"Select priority:"
        )
        await callback.message.edit_text(
            prompt_text,
            reply_markup=get_priority_keyboard(next_task["id"]),
            parse_mode="HTML"
        )
    else:
        pending_all = await get_pending_tasks_for_user(user_id)
        task_summary = "\n".join([f"• [{t['priority'].upper()}] {t['title']}" for t in pending_all if t.get('priority')])
        
        final_text = (
            "🎯 <b>All tasks prioritized and scheduled!</b>\n\n"
            f"📋 <b>Your Active List:</b>\n{task_summary}\n\n"
            "RelentlessBot will now nudge you at your chosen intervals until finished.\n"
            "View anytime with /tasks."
        )
        await callback.message.edit_text(final_text, parse_mode="HTML")

@router.callback_query(F.data.startswith("done:"))
async def handle_done_callback(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = await mark_task_completed(task_id)

    if not task:
        await callback.answer("Task not found.", show_alert=True)
        return

    now_str = datetime.now(settings.tz).strftime("%I:%M %p")
    await callback.answer("Great job! Task marked as completed. 🎉")
    await callback.message.edit_text(
        f"🎉 <b>Completed!</b> <s>{task['title']}</s>\nFinished at {now_str}",
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("drop:"))
async def handle_drop_callback(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    task = await mark_task_dropped(task_id)

    if not task:
        await callback.answer("Task not found.", show_alert=True)
        return

    await callback.answer("Task dropped.")
    await callback.message.edit_text(
        f"🗑️ <b>Dropped:</b> {task['title']}",
        parse_mode="HTML"
    )

@router.callback_query(F.data == "clear_pending")
async def handle_clear_pending(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = await clear_user_tasks(user_id, status_filter="pending")
    await callback.answer(f"Cleared {count} pending tasks.")
    await callback.message.edit_text(f"🗑️ Cleared {count} pending task(s). You have a fresh slate!")

@router.callback_query(F.data == "clear_completed")
async def handle_clear_completed(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = await clear_user_tasks(user_id, status_filter="completed")
    await callback.answer(f"Cleared {count} completed tasks.")
    await callback.message.edit_text(f"🧹 Cleared {count} completed task record(s).")

@router.callback_query(F.data == "cancel_action")
async def handle_cancel_action(callback: CallbackQuery):
    await callback.answer("Action cancelled.")
    await callback.message.edit_text("Cancelled.")

@router.callback_query(F.data == "clear_old_tasks")
async def handle_clear_old(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = await clear_user_tasks(user_id, status_filter="pending")
    await callback.answer("Old tasks cleared.")
    await callback.message.edit_text(f"🗑️ Cleared {count} old task(s). Ready for today's new tasks!")

@router.callback_query(F.data == "keep_old_tasks")
async def handle_keep_old(callback: CallbackQuery):
    await callback.answer("Keeping old tasks active.")
    await callback.message.edit_text("📋 Kept old tasks active! You can still send new ones to append anytime.")
