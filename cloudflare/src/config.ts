export interface Env {
  DB: D1Database;
  BOT_TOKEN: string;
  ALLOWED_USER_IDS?: string;
  TIMEZONE?: string;
  QUIET_HOURS_START?: string;
  QUIET_HOURS_END?: string;
  MORNING_PROMPT_TIME?: string;
  HIGH_PRIORITY_INTERVAL_MINUTES?: string | number;
  MEDIUM_PRIORITY_INTERVAL_MINUTES?: string | number;
  LOW_PRIORITY_INTERVAL_MINUTES?: string | number;
}

export function getAllowedUserIds(env: Env): Set<number> {
  const raw = (env.ALLOWED_USER_IDS || "").trim();
  if (!raw || raw === "*") return new Set();
  const ids = new Set<number>();
  for (const item of raw.split(",")) {
    const trimmed = item.trim();
    if (/^\d+$/.test(trimmed)) {
      ids.add(parseInt(trimmed, 10));
    }
  }
  return ids;
}

export function getLocalTime(env: Env, date: Date = new Date()): { hours: number; minutes: number } {
  const tz = env.TIMEZONE || "Asia/Kolkata";
  try {
    const formatter = new Intl.DateTimeFormat("en-US", {
      timeZone: tz,
      hour: "numeric",
      minute: "numeric",
      hour12: false,
    });
    const parts = formatter.formatToParts(date);
    let hours = 0;
    let minutes = 0;
    for (const part of parts) {
      if (part.type === "hour") hours = parseInt(part.value, 10) % 24;
      if (part.type === "minute") minutes = parseInt(part.value, 10);
    }
    return { hours, minutes };
  } catch {
    return { hours: date.getUTCHours(), minutes: date.getUTCMinutes() };
  }
}

export function isInQuietHours(env: Env, date: Date = new Date()): boolean {
  const startStr = env.QUIET_HOURS_START || "00:00";
  const endStr = env.QUIET_HOURS_END || "07:00";

  const [sH, sM] = startStr.split(":").map(Number);
  const [eH, eM] = endStr.split(":").map(Number);

  const startMins = sH * 60 + sM;
  const endMins = eH * 60 + eM;

  const { hours, minutes } = getLocalTime(env, date);
  const currentMins = hours * 60 + minutes;

  if (startMins === endMins) return false;
  if (startMins < endMins) {
    return currentMins >= startMins && currentMins < endMins;
  } else {
    // Crosses midnight (e.g. 23:00 to 07:00)
    return currentMins >= startMins || currentMins < endMins;
  }
}

export function getIntervalForPriority(priority: string | null | undefined, env: Env): number {
  const p = (priority || "medium").toLowerCase();
  if (p === "high") {
    return Number(env.HIGH_PRIORITY_INTERVAL_MINUTES || 45);
  }
  if (p === "low") {
    return Number(env.LOW_PRIORITY_INTERVAL_MINUTES || 150);
  }
  return Number(env.MEDIUM_PRIORITY_INTERVAL_MINUTES || 90);
}

export function calculateNextReminderTime(intervalMinutes: number, env: Env, fromDate: Date = new Date()): Date {
  const target = new Date(fromDate.getTime() + intervalMinutes * 60 * 1000);

  if (isInQuietHours(env, target)) {
    const endStr = env.QUIET_HOURS_END || "07:00";
    const [eH, eM] = endStr.split(":").map(Number);
    const { hours } = getLocalTime(env, target);
    
    // Calculate how many minutes to add to reach end of quiet hours
    let hoursDiff = eH - hours;
    if (hoursDiff <= 0) hoursDiff += 24;
    
    return new Date(target.getTime() + hoursDiff * 60 * 60 * 1000);
  }

  return target;
}
