export interface User {
  user_id: number;
  chat_id: number;
  username?: string | null;
  first_name?: string | null;
  created_at: string;
}

export interface Task {
  id: number;
  user_id: number;
  chat_id: number;
  title: string;
  priority?: "high" | "medium" | "low" | null;
  status: "pending" | "completed" | "dropped";
  created_at: string;
  last_reminded_at?: string | null;
  next_reminder_at?: string | null;
  completed_at?: string | null;
  remind_count: number;
}

export async function upsertUser(
  db: D1Database,
  userId: number,
  chatId: number,
  username?: string | null,
  firstName?: string | null
): Promise<void> {
  const now = new Date().toISOString();
  await db
    .prepare(
      `INSERT INTO users (user_id, chat_id, username, first_name, created_at)
       VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(user_id) DO UPDATE SET
         chat_id = excluded.chat_id,
         username = excluded.username,
         first_name = excluded.first_name;`
    )
    .bind(userId, chatId, username || null, firstName || null, now)
    .run();
}

export async function getAllUsers(db: D1Database): Promise<User[]> {
  const res = await db.prepare("SELECT * FROM users").all<User>();
  return res.results || [];
}

export async function createTask(
  db: D1Database,
  userId: number,
  chatId: number,
  title: string
): Promise<number> {
  const now = new Date().toISOString();
  const res = await db
    .prepare(
      `INSERT INTO tasks (user_id, chat_id, title, status, created_at)
       VALUES (?, ?, ?, 'pending', ?)`
    )
    .bind(userId, chatId, title, now)
    .run();

  return Number(res.meta.last_row_id);
}

export async function setTaskPriority(
  db: D1Database,
  taskId: number,
  priority: string,
  nextReminderAt: string
): Promise<void> {
  await db
    .prepare(
      `UPDATE tasks
       SET priority = ?, next_reminder_at = ?
       WHERE id = ?`
    )
    .bind(priority, nextReminderAt, taskId)
    .run();
}

export async function getTaskById(db: D1Database, taskId: number): Promise<Task | null> {
  const res = await db
    .prepare("SELECT * FROM tasks WHERE id = ?")
    .bind(taskId)
    .first<Task>();
  return res || null;
}

export async function getPendingTasksForUser(db: D1Database, userId: number): Promise<Task[]> {
  const query = `
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
  `;
  const res = await db.prepare(query).bind(userId).all<Task>();
  return res.results || [];
}

export async function getTasksNeedingPriority(db: D1Database, userId: number): Promise<Task[]> {
  const res = await db
    .prepare(
      `SELECT * FROM tasks
       WHERE user_id = ? AND status = 'pending' AND priority IS NULL
       ORDER BY id ASC`
    )
    .bind(userId)
    .all<Task>();
  return res.results || [];
}

export async function markTaskCompleted(db: D1Database, taskId: number): Promise<Task | null> {
  const now = new Date().toISOString();
  await db
    .prepare(
      `UPDATE tasks
       SET status = 'completed', completed_at = ?, next_reminder_at = NULL
       WHERE id = ?`
    )
    .bind(now, taskId)
    .run();
  return getTaskById(db, taskId);
}

export async function markTaskDropped(db: D1Database, taskId: number): Promise<Task | null> {
  await db
    .prepare(
      `UPDATE tasks
       SET status = 'dropped', next_reminder_at = NULL
       WHERE id = ?`
    )
    .bind(taskId)
    .run();
  return getTaskById(db, taskId);
}

export async function getDueTasks(db: D1Database, currentIsoTime: string): Promise<Task[]> {
  const query = `
    SELECT * FROM tasks
    WHERE status = 'pending' 
      AND priority IS NOT NULL 
      AND next_reminder_at IS NOT NULL
      AND next_reminder_at <= ?
    ORDER BY next_reminder_at ASC;
  `;
  const res = await db.prepare(query).bind(currentIsoTime).all<Task>();
  return res.results || [];
}

export async function updateTaskReminder(
  db: D1Database,
  taskId: number,
  lastRemindedAt: string,
  nextReminderAt: string
): Promise<void> {
  await db
    .prepare(
      `UPDATE tasks
       SET last_reminded_at = ?,
           next_reminder_at = ?,
           remind_count = remind_count + 1
       WHERE id = ?`
    )
    .bind(lastRemindedAt, nextReminderAt, taskId)
    .run();
}

export async function clearUserTasks(
  db: D1Database,
  userId: number,
  statusFilter?: "pending" | "completed"
): Promise<number> {
  let res;
  if (statusFilter) {
    res = await db
      .prepare("DELETE FROM tasks WHERE user_id = ? AND status = ?")
      .bind(userId, statusFilter)
      .run();
  } else {
    res = await db
      .prepare("DELETE FROM tasks WHERE user_id = ?")
      .bind(userId)
      .run();
  }
  return res.meta.changes || 0;
}
