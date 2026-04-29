from datetime import datetime, timezone


def to_local_buckets(ts_iso: str):
    """Convert ISO8601 UTC timestamp to (hour_local 'YYYY-MM-DD HH', day_local 'YYYY-MM-DD')."""
    if not ts_iso:
        now = datetime.now().astimezone()
    else:
        s = ts_iso.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(s)
        except ValueError:
            now = datetime.now().astimezone()
            return now.strftime("%Y-%m-%d %H"), now.strftime("%Y-%m-%d")
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        now = dt.astimezone()
    return now.strftime("%Y-%m-%d %H"), now.strftime("%Y-%m-%d")
