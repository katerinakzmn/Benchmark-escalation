# T011 — original buggy code

import time
from collections import deque
class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls = deque()
    def is_allowed(self) -> bool:
        now = time.time()
        cutoff = now + self.window  # BUG 1: должно быть now - self.window
        while self.calls and self.calls[0] > cutoff:  # BUG 2: должно быть <
            self.calls.popleft()
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(now)
        return True
