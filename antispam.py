"""حماية من السبام — حد أقصى للطلبات في نافذة زمنية"""
import collections
import threading
import time

import config


class RateLimiter:
    def __init__(self, max_requests, window_seconds):
        self.max = max(1, int(max_requests))
        self.window = max(1, int(window_seconds))
        self.hits = {}
        self.lock = threading.Lock()

    def check(self, user_id):
        """بيرجع (مسموح؟, ثواني الانتظار المتبقية)"""
        now = time.time()
        with self.lock:
            dq = self.hits.setdefault(user_id, collections.deque())
            while dq and dq[0] <= now - self.window:
                dq.popleft()
            if len(dq) >= self.max:
                wait = int(dq[0] + self.window - now) + 1
                return False, max(1, wait)
            dq.append(now)
            return True, 0


limiter = RateLimiter(config.RATE_LIMIT_REQUESTS, config.RATE_LIMIT_WINDOW)
