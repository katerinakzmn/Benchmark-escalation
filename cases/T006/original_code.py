# T006 — original buggy code

import time
class TTLCache:
    def __init__(self, ttl: int):
        self.ttl = ttl
        self.store = {}
    def set(self, key: str, value) -> None:
        self.store[key] = (value, time.time())
    def get(self, key: str):
        if key not in self.store:
            return None
        value, ts = self.store[key]
        if ts < self.ttl:  # BUG
            del self.store[key]
            return None
        return value
