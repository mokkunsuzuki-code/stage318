from collections import defaultdict
import time

REQUEST_LOG = defaultdict(list)


def check_rate_limit(api_key, limit):
    now = time.time()
    window_seconds = 86400

    REQUEST_LOG[api_key] = [
        t for t in REQUEST_LOG[api_key]
        if now - t < window_seconds
    ]

    if len(REQUEST_LOG[api_key]) >= limit:
        return False

    REQUEST_LOG[api_key].append(now)
    return True
