from datetime import datetime
from typing import Optional, List, Dict, Any
from src.database.db import get_db_connection
from src.config import settings

async def upsert_user(user_id: int, chat_id: int, username: Optional[str] = None, first_name: Optional[str] = None) -> None:
    """Register or update user details."""
    now = datetime.now(settings.tz).isoformat()
    async with get_db_connection() as db:
        await db.execute("""
            INSERT INTO users (user_id, chat_id, username, first_name, created_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                chat_id = excluded.chat_id,
                username = excluded.username,
                first_name = excluded.first_name;
        """, (user_id, chat_id, username, first_name, now))
        await db.commit()

async def get_all_users() -> List[Dict[str, Any]]:
    """Retrieve all registered users."""
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def create_task(user_id: int, chat_id: int, title: str, priority: Optional[str] = None) -> int:
    """Create a new task and return its ID."""
    now = datetime.now(settings.tz).isoformat()
    async with get_db_connection() as db:
        cursor = await db.execute("""
            INSERT INTO tasks (user_id, chat_id, title, priority, status, created_at)
            VALUES (?, ?, ?, ?, 'pending', ?)
        """, (user_id, chat_id, title, priority, now))
        await db.commit()
        return cursor.lastrowid

async def set_task_priority(task_id: int, priority: str, next_reminder_at: str) -> None:
    """Set the task priority and first reminder schedule."""
    async with get_db_connection() as db:
        await db.execute("""
            UPDATE tasks
            SET priority = ?, next_reminder_at = ?
            WHERE id = ?
        """, (priority, next_reminder_at, task_id))
        await db.commit()

async def get_task_by_id(task_id: int) -> Optional[Dict[str, Any]]:
    """Get a task by its ID."""
    async with get_db_connection() as db:
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_pending_tasks_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all pending tasks for a user ordered by priority (high -> medium -> low -> unassigned)."""
    async with get_db_connection() as db:
        query = """
            SELECT * FROM tasks
            WHERE user_id = ? AND status = 'pending'
            ORDER BY 
                CASE priority
                    WHEN 'high' THEN 1
                    WHEN 'medium' THEN 2
                    WHEN 'low' THEN 3
                    ELSE 4
                END,
                created_at ASC;
        """
        async with db.execute(query, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_tasks_needing_priority(user_id: int) -> List[Dict[str, Any]]:
    """Get tasks for a user that haven't been assigned a priority yet."""
    async with get_db_connection() as db:
        async with db.execute("""
            SELECT * FROM tasks
            WHERE user_id = ? AND status = 'pending' AND priority IS NULL
            ORDER BY id ASC
        """, (user_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def mark_task_completed(task_id: int) -> Optional[Dict[str, Any]]:
    """Mark a task as completed."""
    now = datetime.now(settings.tz).isoformat()
    async with get_db_connection() as db:
        await db.execute("""
            UPDATE tasks
            SET status = 'completed', completed_at = ?, next_reminder_at = NULL
            WHERE id = ?
        """, (now, task_id))
        await db.commit()
    return await get_task_by_id(task_id)

async def mark_task_dropped(task_id: int) -> Optional[Dict[str, Any]]:
    """Mark a task as dropped / deleted."""
    async with get_db_connection() as db:
        await db.execute("""
            UPDATE tasks
            SET status = 'dropped', next_reminder_at = NULL
            WHERE id = ?
        """, (task_id,))
        await db.commit()
    return await get_task_by_id(task_id)

async def get_due_tasks(current_iso_time: str) -> List[Dict[str, Any]]:
    """Find all active tasks whose next reminder is due."""
    async with get_db_connection() as db:
        query = """
            SELECT * FROM tasks
            WHERE status = 'pending' 
              AND priority IS NOT NULL 
              AND next_reminder_at IS NOT NULL
              AND next_reminder_at <= ?
            ORDER BY next_reminder_at ASC;
        """
        async with db.execute(query, (current_iso_time,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def update_task_reminder(task_id: int, last_reminded_at: str, next_reminder_at: str) -> None:
    """Record that a reminder was sent and schedule the next one."""
    async with get_db_connection() as db:
        await db.execute("""
            UPDATE tasks
            SET last_reminded_at = ?,
                next_reminder_at = ?,
                remind_count = remind_count + 1
            WHERE id = ?
        """, (last_reminded_at, next_reminder_at, task_id))
        await db.commit()

async def clear_user_tasks(user_id: int, status_filter: Optional[str] = None) -> int:
    """Clear tasks for a user. If status_filter is provided ('pending' or 'completed'), only those are cleared."""
    async with get_db_connection() as db:
        if status_filter:
            cursor = await db.execute("""
                DELETE FROM tasks WHERE user_id = ? AND status = ?
            """, (user_id, status_filter))
        else:
            cursor = await db.execute("""
                DELETE FROM tasks WHERE user_id = ?
            """, (user_id,))
        await db.commit()
        return cursor.rowcount
