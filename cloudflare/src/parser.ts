const BULLET_PREFIX_REGEX = /^(\s*[-*•–—]\s*|\s*\d+[\.\)]\s*)/;

export function parseTaskInput(rawText: string): string[] {
  const text = rawText.trim();
  if (!text) return [];

  let rawLines: string[];
  if (text.includes("\n")) {
    rawLines = text.split("\n");
  } else {
    rawLines = text.split(",");
  }

  const tasks: string[] = [];
  for (const line of rawLines) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const cleaned = trimmed.replace(BULLET_PREFIX_REGEX, "").trim();
    if (cleaned) {
      tasks.push(cleaned);
    }
  }

  return tasks;
}
