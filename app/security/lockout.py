from datetime import UTC, datetime, timedelta


def utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def is_account_locked(user) -> bool:
    now = utcnow()
    if user.locked_until and user.locked_until <= now:
        user.clear_lockout()
        return False
    return bool(user.locked_until and user.locked_until > now)


def clear_failed_attempts(user) -> None:
    user.clear_lockout()


def record_failed_attempt(user, config: dict) -> bool:
    now = utcnow()
    window_minutes = config.get("LOCKOUT_WINDOW_MINUTES", 15)
    max_attempts = config.get("LOCKOUT_MAX_ATTEMPTS", 5)
    duration_minutes = config.get("LOCKOUT_DURATION_MINUTES", 30)

    window = timedelta(minutes=window_minutes)
    duration = timedelta(minutes=duration_minutes)

    if (
        not user.failed_attempt_window_start
        or now - user.failed_attempt_window_start > window
    ):
        user.failed_attempt_window_start = now
        user.failed_attempts = 1
    else:
        user.failed_attempts += 1

    if user.failed_attempts >= max_attempts:
        user.locked_until = now + duration
        user.failed_attempts = 0
        user.failed_attempt_window_start = None
        return True

    return False
