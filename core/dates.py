from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def is_valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def user_today(user) -> date:
    """Today's date on the user's own calendar, not the server's."""
    return datetime.now(ZoneInfo(user.timezone or "UTC")).date()
