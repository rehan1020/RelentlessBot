from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from src.database.models import (
    upsert_user,
    create_task,
    get_pending_tasks_for_user,
    get_tasks_needing_priority
)
from src.services.parser import parse_task_input
from src.config import settings

router = Router()

def get_priority_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Builds inline keyboard for setting priority on a task."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"🔴 High ({settings.high_priority_interval_minutes}m)",
                    callback_data=f"prio:{task_id}:high"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🟡 Medium ({settings.medium_priority_interval_minutes}m)",
                    callback_data=f"prio:{task_id}:medium"
                )
            ],
            [
                InlineKeyboardButton(
                    text=f"🟢 Low ({settings.low_priority_interval_minutes}m)",
                    callback_data=f"prio:{task_id}:low"
                )
            ]
        ]
    )

@router.message(Command("tasks", "list"))
async def handle_list_tasks(message: Message):
    user_id = message.from_user.id
    tasks = await get_pending_tasks_for_user(user_id)

    if not tasks:
        await message.answer(
            "🎉 <b>You have no pending tasks!</b>\n\n"
            "Send me your tasks (separated by newlines or commas) to start tracking.",
            parse_mode="HTML"
        )
        return

    high = [t for t in tasks if t["priority"] == "high"]
    med = [t for t in tasks if t["priority"] == "medium"]
    low = [t for t in tasks if t["priority"] == "low"]
    unassigned = [t for t in tasks if not t["priority"]]

    lines = ["📋 <b>Your Active Tasks:</b>\n"]

    if high:
        lines.append(f"🔴 <b>High Priority ({settings.high_priority_interval_minutes}m reminder):</b>")
        for t in high:
            lines.append(f"  • {t['title']}")
        lines.append("")

    if med:
        lines.append(f"🟡 <b>Medium Priority ({settings.medium_priority_interval_minutes}m reminder):</b>")
        for t in med:
            lines.append(f"  • {t['title']}")
        lines.append("")

    if low:
        lines.append(f"🟢 <b>Low Priority ({settings.low_priority_interval_minutes}m reminder):</b>")
        for t in low:
            lines.append(f"  • {t['title']}")
        lines.append("")

    if unassigned:
        lines.append("⚪ <b>Awaiting Priority:</b>")
        for t in unassigned:
            lines.append(f"  • {t['title']}")
        lines.append("")

    # Add quick-action completion buttons (one row per task, up to 5 at a time)
    keyboard_buttons = []
    for t in tasks[:6]:
        keyboard_buttons.append([
            InlineKeyboardButton(text=f"✅ Mark Done: {t['title'][:25]}", callback_data=f"done:{t['id']}")
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons) if keyboard_buttons else None
    await message.answer("\n".join(lines), reply_markup=keyboard, parse_mode="HTML")

@router.message(Command("clear", "reset"))
async def handle_clear_command(message: Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑️ Clear All Pending Tasks", callback_data="clear_pending"),
            ],
            [
                InlineKeyboardButton(text="🧹 Clear Completed History", callback_data="clear_completed"),
            ],
            [
                InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action"),
            ]
        ]
    )
    await message.answer(
        "⚠️ <b>Task Management / Reset:</b>\nWhat would you like to clear?",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

@router.message(F.text, ~F.text.startswith("/"))
async def handle_incoming_tasks(message: Message):
    user = message.from_user
    if not user:
        return

    # Upsert user record
    await upsert_user(
        user_id=user.id,
        chat_id=message.chat.id,
        username=user.username,
        first_name=user.first_name
    )

    parsed_titles = parse_task_input(message.text)
    if not parsed_titles:
        await message.answer("I couldn't detect any tasks. Please send task names separated by commas or newlines.")
        return

    created_ids = []
    for title in parsed_titles:
        t_id = await create_task(user_id=user.id, chat_id=message.chat.id, title=title)
        created_ids.append(t_id)

    # Prompt priority for the newly created tasks
    needing_priority = await get_tasks_needing_priority(user.id)
    if not needing_priority:
        return

    first_task = needing_priority[0]
    total_unassigned = len(needing_priority)

    prompt_text = (
        f"📝 <b>Added {len(parsed_titles)} task(s)!</b>\n\n"
        f"Let's set their priority so I know how often to remind you.\n\n"
        f"Task <b>(1/{total_unassigned})</b>:\n"
        f"👉 <b>{first_task['title']}</b>\n\n"
        f"How important is this task?"
    )

    await message.answer(
        prompt_text,
        reply_markup=get_priority_keyboard(first_task["id"]),
        parse_mode="HTML"
    )
