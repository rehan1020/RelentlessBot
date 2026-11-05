"""Task list parser supporting multiple formats."""
import re
from typing import List

BULLET_PREFIX_REGEX = re.compile(r"^(\s*[-*•–—]\s*|\s*\d+[\.\)]\s*)")

def parse_task_input(raw_text: str) -> List[str]:
    """
    Parses user input into individual tasks.
    Supports:
    - Multi-line lists (newline separated)
    - Comma-separated lists (e.g. 'Task 1, Task 2, Task 3')
    - Bullet points ('- Task', '* Task', '• Task')
    - Numbered lists ('1. Task', '2) Task')
    """
    text = raw_text.strip()
    if not text:
        return []

    # If the text has newlines, split primarily by newlines
    if "\n" in text:
        raw_lines = text.split("\n")
    else:
        # If single line with commas, split by comma
        raw_lines = text.split(",")

    tasks = []
    for line in raw_lines:
        line = line.strip()
        if not line:
            continue
        
        # Remove bullet points or numbering
        cleaned = BULLET_PREFIX_REGEX.sub("", line).strip()
        if cleaned:
            tasks.append(cleaned)

    return tasks
