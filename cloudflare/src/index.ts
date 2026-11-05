import { webhookCallback } from "grammy";
import { Env } from "./config";
import { createBot, registerBotCommands } from "./bot";
import { processCronTick } from "./scheduler";

export default {
  async fetch(request: Request, env: Env, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);

    if (!env.BOT_TOKEN) {
      return new Response("BOT_TOKEN is not configured in worker secrets.", { status: 500 });
    }

    const bot = createBot(env);

    // 1. One-click Webhook & Command Registration URL: https://<worker>.workers.dev/set-webhook
    if (url.pathname === "/set-webhook") {
      const webhookUrl = `${url.origin}/webhook`;
      try {
        await bot.api.setWebhook(webhookUrl);
        await registerBotCommands(bot);
        return new Response(
          `<html><body style="font-family:sans-serif;text-align:center;padding:50px;">` +
            `<h2 style="color:green;">✅ Webhook & Bot Commands Registered!</h2>` +
            `<p>Telegram is now forwarding messages to: <code>${webhookUrl}</code></p>` +
            `<p>Commands menu (/tasks, /clear, /help, /start) is now enabled in Telegram!</p>` +
            `<p>Open Telegram and message your bot to start!</p>` +
            `</body></html>`,
          { headers: { "Content-Type": "text/html" } }
        );
      } catch (err: any) {
        return new Response(`Failed to set webhook: ${err.message}`, { status: 500 });
      }
    }

    // 2. Telegram Webhook Callback
    if (url.pathname === "/webhook" && request.method === "POST") {
      const handleUpdate = webhookCallback(bot, "cloudflare-mod");
      return handleUpdate(request);
    }

    // 3. Status Health Check
    return new Response(
      JSON.stringify(
        {
          name: "RelentlessBot",
          status: "online",
          platform: "Cloudflare Workers",
          version: "1.0.0",
        },
        null,
        2
      ),
      { headers: { "Content-Type": "application/json" } }
    );
  },

  // Background Cron Trigger (runs every 1 minute)
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    if (!env.BOT_TOKEN) return;
    ctx.waitUntil(processCronTick(env));
  },
};
