"""Rate limiting and retry helpers (protocols S8/S9)."""

import time
from functools import wraps

import requests


def rate_limit(calls_per_second: float = 1):
    """Decorator enforcing a minimum interval between calls."""
    min_interval = 1.0 / calls_per_second
    state = {"last_called": 0.0}

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - state["last_called"]
            wait = min_interval - elapsed
            if wait > 0:
                time.sleep(wait)
            result = func(*args, **kwargs)
            state["last_called"] = time.time()
            return result

        return wrapper

    return decorator


def safe_request(url: str, params: dict, max_retries: int = 3, timeout: int = 15):
    """GET with retry + exponential backoff on 429/timeout. Returns Response or None."""
    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params, timeout=timeout)
            if res.status_code == 200:
                return res
            if res.status_code == 429:
                wait = 2**attempt
                print(f"⚠️ Rate limited. Waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"⚠️ HTTP {res.status_code}")
        except requests.exceptions.Timeout:
            print(f"⚠️ Timeout (attempt {attempt + 1}/{max_retries})")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ Error: {exc}")
            break
    return None
