import { Bot, Context, InlineKeyboard } from "grammy";
import { Env, getAllowedUserIds, getIntervalForPriority, calculateNextReminderTime } from "./config";
import {
  upsertUser,
  createTask,
  getTasksNeedingPriority,
  getPendingTasksForUser,
  getTaskById,
  setTaskPriority,
  markTaskCompleted,
  markTaskDropped,
  clearUserTasks,
} from "./database";
import { parseTaskInput } from "./parser";

export interface BotContext extends Context {
  env: Env;
}

export function buildPriorityKeyboard(taskId: number, env: Env): InlineKeyboard {
  const highMin = env.HIGH_PRIORITY_INTERVAL_MINUTES || 45;
  const medMin = env.MEDIUM_PRIORITY_INTERVAL_MINUTES || 90;
  const lowMin = env.LOW_PRIORITY_INTERVAL_MINUTES || 150;

  return new InlineKeyboard()
    .text(`🔴 High (${highMin}m)`, `prio:${taskId}:high`)
    .row()
    .text(`🟡 Medium (${medMin}m)`, `prio:${taskId}:medium`)
    .row()
    .text(`🟢 Low (${lowMin}m)`, `prio:${taskId}:low`);
}

export function createBot(env: Env): Bot<BotContext> {
  const bot = new Bot<BotContext>(env.BOT_TOKEN);

  // 1. Attach environment to context FIRST
  bot.use(async (ctx, next) => {
    ctx.env = env;
    await next();
  });

  // 2. Whitelist Middleware
  bot.use(async (ctx, next) => {
    const allowed = getAllowedUserIds(ctx.env);
    if (allowed.size === 0) return next();

    const userId = ctx.from?.id;
    if (!userId || !allowed.has(userId)) {
      if (ctx.callbackQuery) {
        await ctx.answerCallbackQuery({ text: "Access Denied.", show_alert: true });
        return;
      }
      await ctx.reply(
        `⛔ <b>Access Denied</b>\n\n` +
          `This is a private self-hosted <b>RelentlessBot</b> on Cloudflare Workers.\n\n` +
          `Your Telegram User ID is: <code>${userId}</code>\n\n` +
          `Add it to <code>ALLOWED_USER_IDS</code> in your <code>wrangler.toml</code>.`,
        { parse_mode: "HTML" }
      );
      return;
    }
    return next();
  });

  // /start command
  bot.command("start", async (ctx) => {
    if (ctx.from && ctx.chat) {
      await upsertUser(
        ctx.env.DB,
        ctx.from.id,
        ctx.chat.id,
        ctx.from.username,
        ctx.from.first_name
      );
    }

    const qStart = ctx.env.QUIET_HOURS_START || "00:00";
    const qEnd = ctx.env.QUIET_HOURS_END || "07:00";

    const text =
      `👋 <b>Welcome to RelentlessBot (Cloudflare Edition)!</b>\n\n` +
      `I am running 24/7 on Cloudflare Workers edge. I make sure your daily to-dos ` +
      `get done by nagging you persistently until you complete them.\n\n` +
      `⚡ <b>How it works:</b>\n` +
      `1. <b>Send your tasks:</b> Lines or comma-separated.\n` +
      `2. <b>Set priority:</b> 🔴 High, 🟡 Medium, or 🟢 Low.\n` +
      `3. <b>Relentless Nudges:</b> No snooze. I ping you until you tap [✅ Done].\n` +
      `4. <b>Quiet Hours:</b> Silent between <code>${qStart}</code> and <code>${qEnd}</code>.\n\n` +
      `📌 <b>Commands:</b>\n` +
      `• /tasks — View pending tasks\n` +
      `• /clear — Reset or clear tasks\n` +
      `• /help — Full instructions\n\n` +
      `👉 <i>Send me your to-do list right now!</i>`;

    await ctx.reply(text, { parse_mode: "HTML" });
  });

  // /help command
  bot.command("help", async (ctx) => {
    const high = ctx.env.HIGH_PRIORITY_INTERVAL_MINUTES || 45;
    const med = ctx.env.MEDIUM_PRIORITY_INTERVAL_MINUTES || 90;
    const low = ctx.env.LOW_PRIORITY_INTERVAL_MINUTES || 150;

    const text =
      `📖 <b>RelentlessBot Help & Usage</b>\n\n` +
      `<b>Adding Tasks:</b>\n` +
      `Simply send a message with your tasks:\n` +
      `• <b>Newlines:</b>\n` +
      `  Fix deployment bug\n` +
      `  Respond to client\n` +
      `  Go to gym\n\n` +
      `• <b>Commas:</b>\n` +
      `  Fix deployment bug, Respond to client, Go to gym\n\n` +
      `<b>Reminder Intervals:</b>\n` +
      `• 🔴 High: Every ${high} minutes\n` +
      `• 🟡 Medium: Every ${med} minutes\n` +
      `• 🟢 Low: Every ${low} minutes\n\n` +
      `<b>Commands:</b>\n` +
      `• /tasks — List pending tasks\n` +
      `• /clear — Clear tasks\n` +
      `• /start — Welcome overview`;

    await ctx.reply(text, { parse_mode: "HTML" });
  });

  // /tasks command
  bot.command(["tasks", "list"], async (ctx) => {
    const userId = ctx.from?.id;
    if (!userId) return;

    const tasks = await getPendingTasksForUser(ctx.env.DB, userId);
    if (tasks.length === 0) {
      await ctx.reply(
        `🎉 <b>You have no pending tasks!</b>\n\nSend me your tasks (separated by commas or newlines) to start tracking.`,
        { parse_mode: "HTML" }
      );
      return;
    }

    const high = tasks.filter((t) => t.priority === "high");
    const med = tasks.filter((t) => t.priority === "medium");
    const low = tasks.filter((t) => t.priority === "low");
    const unassigned = tasks.filter((t) => !t.priority);

    const lines: string[] = ["📋 <b>Your Active Tasks:</b>\n"];
    if (high.length) {
      lines.push(`🔴 <b>High Priority:</b>`);
      high.forEach((t) => lines.push(`  • ${t.title}`));
      lines.push("");
    }
    if (med.length) {
      lines.push(`🟡 <b>Medium Priority:</b>`);
      med.forEach((t) => lines.push(`  • ${t.title}`));
      lines.push("");
    }
    if (low.length) {
      lines.push(`🟢 <b>Low Priority:</b>`);
      low.forEach((t) => lines.push(`  • ${t.title}`));
      lines.push("");
    }
    if (unassigned.length) {
      lines.push(`⚪ <b>Awaiting Priority:</b>`);
      unassigned.forEach((t) => lines.push(`  • ${t.title}`));
      lines.push("");
    }

    const keyboard = new InlineKeyboard();
    for (const t of tasks.slice(0, 6)) {
      keyboard.text(`✅ Done: ${t.title.slice(0, 25)}`, `done:${t.id}`).row();
    }

    await ctx.reply(lines.join("\n"), { reply_markup: keyboard, parse_mode: "HTML" });
  });

  // /clear command
  bot.command(["clear", "reset"], async (ctx) => {
    const keyboard = new InlineKeyboard()
      .text("🗑️ Clear All Pending", "clear_pending")
      .row()
      .text("🧹 Clear Completed History", "clear_completed")
      .row()
      .text("❌ Cancel", "cancel_action");

    await ctx.reply(
      "⚠️ <b>Task Management / Reset:</b>\nWhat would you like to clear?",
      { reply_markup: keyboard, parse_mode: "HTML" }
    );
  });

  // Priority Callback
  bot.callbackQuery(/^prio:(\d+):([a-z]+)$/, async (ctx) => {
    const match = ctx.match;
    const taskId = parseInt(match[1], 10);
    const priority = match[2];
    const userId = ctx.from.id;

    const task = await getTaskById(ctx.env.DB, taskId);
    if (!task) {
      await ctx.answerCallbackQuery({ text: "Task not found.", show_alert: true });
      return;
    }

    const interval = getIntervalForPriority(priority, ctx.env);
    const nextTime = calculateNextReminderTime(interval, ctx.env);

    await setTaskPriority(ctx.env.DB, taskId, priority, nextTime.toISOString());
    await ctx.answerCallbackQuery({ text: `Set to ${priority.toUpperCase()} (${interval}m)` });

    const remaining = await getTasksNeedingPriority(ctx.env.DB, userId);
    if (remaining.length > 0) {
      const nextTask = remaining[0];
      const prompt =
        `✅ Saved priority for <i>"${task.title}"</i>.\n\n` +
        `Next task <b>(${remaining.length} remaining)</b>:\n` +
        `👉 <b>${nextTask.title}</b>\n\n` +
        `Select priority:`;
      await ctx.editMessageText(prompt, {
        reply_markup: buildPriorityKeyboard(nextTask.id, ctx.env),
        parse_mode: "HTML",
      });
    } else {
      const pendingAll = await getPendingTasksForUser(ctx.env.DB, userId);
      const summary = pendingAll
        .filter((t) => t.priority)
        .map((t) => `• [${t.priority?.toUpperCase()}] ${t.title}`)
        .join("\n");

      await ctx.editMessageText(
        `🎯 <b>All tasks prioritized and scheduled!</b>\n\n` +
          `📋 <b>Your Active List:</b>\n${summary}\n\n` +
          `RelentlessBot will now nudge you at your chosen intervals until finished.\n` +
          `View anytime with /tasks.`,
        { parse_mode: "HTML" }
      );
    }
  });

  // Done Callback
  bot.callbackQuery(/^done:(\d+)$/, async (ctx) => {
    const taskId = parseInt(ctx.match[1], 10);
    const task = await markTaskCompleted(ctx.env.DB, taskId);
    if (!task) {
      await ctx.answerCallbackQuery({ text: "Task not found." });
      return;
    }

    await ctx.answerCallbackQuery({ text: "Great job! Task completed. 🎉" });
    await ctx.editMessageText(`🎉 <b>Completed!</b> <s>${task.title}</s>`, {
      parse_mode: "HTML",
    });
  });

  // Drop Callback
  bot.callbackQuery(/^drop:(\d+)$/, async (ctx) => {
    const taskId = parseInt(ctx.match[1], 10);
    const task = await markTaskDropped(ctx.env.DB, taskId);
    if (!task) {
      await ctx.answerCallbackQuery({ text: "Task not found." });
      return;
    }

    await ctx.answerCallbackQuery({ text: "Task dropped." });
    await ctx.editMessageText(`🗑️ <b>Dropped:</b> ${task.title}`, {
      parse_mode: "HTML",
    });
  });

  // Clear Callbacks
  bot.callbackQuery("clear_pending", async (ctx) => {
    const count = await clearUserTasks(ctx.env.DB, ctx.from.id, "pending");
    await ctx.answerCallbackQuery({ text: `Cleared ${count} tasks.` });
    await ctx.editMessageText(`🗑️ Cleared ${count} pending task(s). Fresh start!`);
  });

  bot.callbackQuery("clear_completed", async (ctx) => {
    const count = await clearUserTasks(ctx.env.DB, ctx.from.id, "completed");
    await ctx.answerCallbackQuery({ text: `Cleared ${count} completed tasks.` });
    await ctx.editMessageText(`🧹 Cleared ${count} completed task records.`);
  });

  bot.callbackQuery("cancel_action", async (ctx) => {
    await ctx.answerCallbackQuery({ text: "Cancelled." });
    await ctx.editMessageText("Action cancelled.");
  });

  bot.callbackQuery("clear_old_tasks", async (ctx) => {
    const count = await clearUserTasks(ctx.env.DB, ctx.from.id, "pending");
    await ctx.answerCallbackQuery({ text: "Old tasks cleared." });
    await ctx.editMessageText(`🗑️ Cleared ${count} old task(s). Ready for today's new tasks!`);
  });

  bot.callbackQuery("keep_old_tasks", async (ctx) => {
    await ctx.answerCallbackQuery({ text: "Keeping old tasks active." });
    await ctx.editMessageText("📋 Kept old tasks active! Send new tasks to append anytime.");
  });

  // Incoming text messages (Tasks)
  bot.on("message:text", async (ctx) => {
    if (ctx.message.text.startsWith("/")) return;

    if (ctx.from && ctx.chat) {
      await upsertUser(
        ctx.env.DB,
        ctx.from.id,
        ctx.chat.id,
        ctx.from.username,
        ctx.from.first_name
      );
    }

    const titles = parseTaskInput(ctx.message.text);
    if (titles.length === 0) {
      await ctx.reply("I couldn't detect any tasks. Please send tasks separated by commas or newlines.");
      return;
    }

    for (const title of titles) {
      await createTask(ctx.env.DB, ctx.from.id, ctx.chat.id, title);
    }

    const needing = await getTasksNeedingPriority(ctx.env.DB, ctx.from.id);
    if (needing.length === 0) return;

    const first = needing[0];
    const prompt =
      `📝 <b>Added ${titles.length} task(s)!</b>\n\n` +
      `Let's set their priority so I know how often to remind you.\n\n` +
      `Task <b>(1/${needing.length})</b>:\n` +
      `👉 <b>${first.title}</b>\n\n` +
      `How important is this task?`;

    await ctx.reply(prompt, {
      reply_markup: buildPriorityKeyboard(first.id, ctx.env),
      parse_mode: "HTML",
    });
  });

  return bot;
}

export async function registerBotCommands(bot: Bot<BotContext>): Promise<void> {
  await bot.api.setMyCommands([
    { command: "start", description: "Start the bot & get welcome info" },
    { command: "tasks", description: "View active tasks & progress" },
    { command: "clear", description: "Clear or reset tasks" },
    { command: "help", description: "Show usage instructions" },
  ]);
}
