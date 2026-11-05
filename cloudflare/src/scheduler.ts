import { Bot, InlineKeyboard } from "grammy";
import {
  Env,
  isInQuietHours,
  getLocalTime,
  getIntervalForPriority,
  calculateNextReminderTime,
} from "./config";
import {
  getDueTasks,
  updateTaskReminder,
  getAllUsers,
  getPendingTasksForUser,
} from "./database";

export async function processCronTick(env: Env): Promise<void> {
  const bot = new Bot(env.BOT_TOKEN);
  const now = new Date();

  // 1. Process Due Task Reminders (Only outside Quiet Hours)
  if (!isInQuietHours(env, now)) {
    try {
      const due = await getDueTasks(env.DB, now.toISOString());
      for (const task of due) {
        const priority = task.priority || "medium";
        const icon = priority === "high" ? "🔴" : priority === "low" ? "🟢" : "🟡";
        const count = task.remind_count + 1;

        const text =
          `⏰ <b>Relentless Nudge #${count}!</b>\n\n` +
          `${icon} <b>[${priority.toUpperCase()}]</b> ${task.title}\n` +
          `Status: Incomplete\n\n` +
          `<i>No excuses. Mark it done once finished!</i>`;

        const keyboard = new InlineKeyboard()
          .text("✅ Done", `done:${task.id}`)
          .text("❌ Drop", `drop:${task.id}`);

        try {
          await bot.api.sendMessage(task.chat_id, text, {
            reply_markup: keyboard,
            parse_mode: "HTML",
          });
        } catch (err) {
          console.error(`Failed to send reminder to chat ${task.chat_id}:`, err);
        }

        const interval = getIntervalForPriority(priority, env);
        const nextTime = calculateNextReminderTime(interval, env, now);
        await updateTaskReminder(
          env.DB,
          task.id,
          now.toISOString(),
          nextTime.toISOString()
        );
      }
    } catch (err) {
      console.error("Error processing due reminders in Cron:", err);
    }
  }

  // 2. Check Daily Morning Prompt (runs at MORNING_PROMPT_TIME, e.g. 07:05)
  const promptTimeStr = env.MORNING_PROMPT_TIME || "07:05";
  const [pH, pM] = promptTimeStr.split(":").map(Number);
  const { hours, minutes } = getLocalTime(env, now);

  if (hours === pH && minutes === pM) {
    try {
      const users = await getAllUsers(env.DB);
      for (const user of users) {
        const pending = await getPendingTasksForUser(env.DB, user.user_id);
        let msg =
          `☀️ <b>Good morning! Time to conquer the day.</b>\n\n` +
          `What is your to-do list for today?\n` +
          `Send your tasks separated by <b>newlines</b> or <b>commas</b>.\n\n` +
          `<i>Example:</i>\n` +
          `• Fix auth bug\n` +
          `• Call team lead\n` +
          `• Go to gym`;

        let keyboard: InlineKeyboard | undefined = undefined;

        if (pending.length > 0) {
          const listStr = pending
            .map((t) => `• ${t.title} (${t.priority || "no priority"})`)
            .join("\n");

          msg +=
            `\n\n📌 <b>You also have ${pending.length} unfinished task(s) from earlier:</b>\n` +
            listStr;

          keyboard = new InlineKeyboard()
            .text("📋 Keep All", "keep_old_tasks")
            .text("🗑️ Clear Old Tasks", "clear_old_tasks");
        }

        try {
          await bot.api.sendMessage(user.chat_id, msg, {
            reply_markup: keyboard,
            parse_mode: "HTML",
          });
        } catch (err) {
          console.error(`Failed to send morning prompt to user ${user.user_id}:`, err);
        }
      }
    } catch (err) {
      console.error("Error sending morning prompt in Cron:", err);
    }
  }
}
