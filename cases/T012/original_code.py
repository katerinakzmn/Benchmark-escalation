from collections import OrderedDict

class LRUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        # не вызывается move_to_end → LRU-порядок не обновляется
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            del self.cache[key]  # удаляем и вставляем заново вместо move_to_end
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=True)  # удаляем ПОСЛЕДНИЙ вместо первого (most recent вместо least recent)
