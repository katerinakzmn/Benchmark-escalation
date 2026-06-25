import time

class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float):
        self.max_calls = max_calls
        self.window = window_seconds
        self.calls = []  # должен быть deque для эффективности

    def is_allowed(self) -> bool:
        now = time.time()
        cutoff = now + self.window  # неверное направление окна
        self.calls = [t for t in self.calls if t > cutoff]  # неверное условие фильтрации
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(now)
        return True
