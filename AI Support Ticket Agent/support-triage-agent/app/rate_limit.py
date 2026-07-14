import re
import time
from groq import RateLimitError

FREE_TIER_RPM = 25  
MIN_SECONDS_BETWEEN_REQUESTS = 60 / FREE_TIER_RPM  

_last_request_time = 0.0


class DailyQuotaExhausted(Exception):
    """Raised when the suggested retry wait is long enough (>2 min) that
    it's clearly a daily/larger quota, not a per-minute one -- retrying
    immediately won't help."""
    pass


def _extract_wait_seconds(message: str) -> float:
    """
    Groq's rate-limit error messages look like:
    'Please try again in 4.42s' or 'Please try again in 6m11.52s'.
    Parse the suggested wait; default to a short conservative wait if the
    message format doesn't match (e.g. Groq changes their wording).
    """
    match = re.search(r"(?:(\d+)m)?([\d.]+)s", message)
    if not match:
        return 10.0
    minutes = int(match.group(1)) if match.group(1) else 0
    seconds = float(match.group(2))
    return minutes * 60 + seconds


def paced_call(fn, *args, max_retries: int = 5, **kwargs):
    """
    Call fn(*args, **kwargs), pacing so we don't exceed FREE_TIER_RPM,
    and retrying with the wait time Groq itself suggests if we still get
    rate-limited. Fails fast with a clear message if the suggested wait
    is long enough to indicate a daily quota rather than a per-minute one.
    """
    global _last_request_time

    elapsed = time.time() - _last_request_time
    if elapsed < MIN_SECONDS_BETWEEN_REQUESTS:
        time.sleep(MIN_SECONDS_BETWEEN_REQUESTS - elapsed)

    for attempt in range(max_retries):
        try:
            result = fn(*args, **kwargs)
            _last_request_time = time.time()
            return result
        except RateLimitError as e:
            wait = _extract_wait_seconds(str(e))

            if wait > 120:
                raise DailyQuotaExhausted(
                    f"Groq suggested waiting {wait:.0f}s, which is long enough "
                    "to indicate a larger (likely daily) quota, not a per-minute "
                    "limit -- retrying won't help right now. Check your usage at "
                    "https://console.groq.com/settings/limits."
                ) from e

            print(f"      rate limited, waiting {wait:.1f}s before retry "
                  f"({attempt + 1}/{max_retries})...")
            time.sleep(wait)

    raise RuntimeError(
        f"Still rate-limited after {max_retries} retries. "
        "Wait a bit and rerun, or lower FREE_TIER_RPM further."
    )
