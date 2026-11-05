import os
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import aiosqlite
from src.config import settings

@asynccontextmanager
async def get_db_connection() -> AsyncGenerator[aiosqlite.Connection, None]:
    """Async context manager yielding a configured SQLite connection."""
    db_file = Path(settings.db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)
    
    async with aiosqlite.connect(str(db_file)) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA journal_mode = WAL;")
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn

async def init_db() -> None:
    """Initialize database tables and indexes."""
    async with get_db_connection() as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL
            );
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                priority TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL,
                last_reminded_at TEXT,
                next_reminder_at TEXT,
                completed_at TEXT,
                remind_count INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            );
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_user_status 
            ON tasks (user_id, status);
        """)

        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_tasks_reminder 
            ON tasks (status, priority, next_reminder_at);
        """)

        await db.commit()
