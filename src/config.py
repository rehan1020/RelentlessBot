import os
from datetime import datetime, time
from typing import Set
import pytz
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    bot_token: str = Field(default="", validation_alias="BOT_TOKEN")
    allowed_user_ids_raw: str = Field(default="", validation_alias="ALLOWED_USER_IDS")
    timezone: str = Field(default="Asia/Kolkata", validation_alias="TIMEZONE")
    
    quiet_hours_start: str = Field(default="00:00", validation_alias="QUIET_HOURS_START")
    quiet_hours_end: str = Field(default="07:00", validation_alias="QUIET_HOURS_END")
    morning_prompt_time: str = Field(default="07:05", validation_alias="MORNING_PROMPT_TIME")

    high_priority_interval_minutes: int = Field(default=45, validation_alias="HIGH_PRIORITY_INTERVAL_MINUTES")
    medium_priority_interval_minutes: int = Field(default=90, validation_alias="MEDIUM_PRIORITY_INTERVAL_MINUTES")
    low_priority_interval_minutes: int = Field(default=150, validation_alias="LOW_PRIORITY_INTERVAL_MINUTES")

    db_path: str = Field(default="data/relentless.db", validation_alias="DB_PATH")

    @property
    def allowed_user_ids(self) -> Set[int]:
        """Parsed set of Telegram user IDs permitted to use the bot."""
        raw = self.allowed_user_ids_raw.strip()
        if not raw or raw == "*":
            return set()
        ids = set()
        for item in raw.split(","):
            cleaned = item.strip()
            if cleaned.isdigit():
                ids.add(int(cleaned))
        return ids

    @property
    def tz(self):
        """Returns the pytz timezone object."""
        try:
            return pytz.timezone(self.timezone)
        except Exception:
            return pytz.UTC

    def get_quiet_time_range(self) -> tuple[time, time]:
        """Parse quiet hours start and end as time objects."""
        s_h, s_m = map(int, self.quiet_hours_start.split(":"))
        e_h, e_m = map(int, self.quiet_hours_end.split(":"))
        return time(s_h, s_m), time(e_h, e_m)

    def is_in_quiet_hours(self, dt: datetime | None = None) -> bool:
        """
        Check if a given datetime (or now in configured timezone) falls into quiet hours.
        Accurately handles spans crossing midnight (e.g., 23:00 to 07:00) as well as 00:00 to 07:00.
        """
        if dt is None:
            dt = datetime.now(self.tz)
        elif dt.tzinfo is None:
            dt = self.tz.localize(dt)
        else:
            dt = dt.astimezone(self.tz)

        t = dt.time()
        start, end = self.get_quiet_time_range()

        if start == end:
            return False
        if start < end:
            return start <= t < end
        else:
            # Over midnight (e.g. 23:00 to 07:00)
            return t >= start or t < end

    def get_interval_for_priority(self, priority: str) -> int:
        """Returns reminder interval in minutes for a given priority."""
        p = priority.lower() if priority else "medium"
        if p == "high":
            return self.high_priority_interval_minutes
        elif p == "low":
            return self.low_priority_interval_minutes
        return self.medium_priority_interval_minutes


# Global settings instance
settings = Settings()
