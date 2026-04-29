"""
developer.py — агент-разработчик.

Роль: получить задачу → написать код.
НЕ принимает решений об эскалации — это не его дело.
Может получать подсказки от ревьюера и переписывать код.

В прототипе: mock-реализация с заранее заданными ответами.
В реальной системе: вызов LLM API с промптом вида
  "Ты опытный разработчик. Вот задача: {description}. Напиши код."
"""

from agents.base import AgentRole, ModelTier, Message


class DeveloperAgent:
    """
    Агент-разработчик. Существует в двух вариантах:
    - WEAK:   дешёвая модель, часто ошибается на сложных задачах
    - STRONG: дорогая модель, справляется с большинством задач
    """

    role = AgentRole.DEVELOPER

    # Mock-решения: задача → {уровень → {попытка → код}}
    _SOLUTIONS = {
        "T001": {
            ModelTier.WEAK:   {1: "def solution(a, b):\n    return a + b"},
            ModelTier.STRONG: {1: "def solution(a, b):\n    return a + b"},
        },
        "T002": {
            ModelTier.WEAK: {
                # Первая попытка: забывает про делимость на 15
                1: (
                    "def solution(n):\n"
                    "    if n % 3 == 0:\n"
                    "        return 'Fizz'\n"
                    "    elif n % 5 == 0:\n"
                    "        return 'Buzz'\n"
                    "    return str(n)"
                ),
                # После подсказки от ревьюера — исправляется
                2: (
                    "def solution(n):\n"
                    "    if n % 15 == 0:\n"
                    "        return 'FizzBuzz'\n"
                    "    elif n % 3 == 0:\n"
                    "        return 'Fizz'\n"
                    "    elif n % 5 == 0:\n"
                    "        return 'Buzz'\n"
                    "    return str(n)"
                ),
            },
            ModelTier.STRONG: {
                1: (
                    "def solution(n):\n"
                    "    if n % 15 == 0:\n"
                    "        return 'FizzBuzz'\n"
                    "    elif n % 3 == 0:\n"
                    "        return 'Fizz'\n"
                    "    elif n % 5 == 0:\n"
                    "        return 'Buzz'\n"
                    "    return str(n)"
                ),
            },
        },
        "T003": {
            ModelTier.WEAK: {
                # Слабая модель не реализует LRU корректно
                1: (
                    "class LRUCache:\n"
                    "    def __init__(self, capacity):\n"
                    "        self.cap = capacity\n"
                    "        self.cache = {}\n"
                    "    def get(self, key):\n"
                    "        return self.cache.get(key, -1)\n"
                    "    def put(self, key, value):\n"
                    "        if len(self.cache) >= self.cap and key not in self.cache:\n"
                    "            self.cache.pop(next(iter(self.cache)))\n"
                    "        self.cache[key] = value"
                ),
                # Даже после подсказки слабая модель не справляется
                2: (
                    "class LRUCache:\n"
                    "    def __init__(self, capacity):\n"
                    "        self.cap = capacity\n"
                    "        self.cache = {}\n"
                    "        self.order = []\n"
                    "    def get(self, key):\n"
                    "        if key in self.cache:\n"
                    "            self.order.remove(key)\n"
                    "            self.order.append(key)\n"
                    "            return self.cache[key]\n"
                    "        return -1\n"
                    "    def put(self, key, value):\n"
                    "        if key in self.cache:\n"
                    "            self.order.remove(key)\n"
                    "        elif len(self.cache) >= self.cap:\n"
                    "            lru = self.order.pop(0)\n"
                    "            del self.cache[lru]\n"
                    "        self.cache[key] = value\n"
                    "        self.order.append(key)"
                ),
            },
            ModelTier.STRONG: {
                1: (
                    "from collections import OrderedDict\n\n"
                    "class LRUCache:\n"
                    "    def __init__(self, capacity):\n"
                    "        self.cap = capacity\n"
                    "        self.cache = OrderedDict()\n\n"
                    "    def get(self, key):\n"
                    "        if key not in self.cache:\n"
                    "            return -1\n"
                    "        self.cache.move_to_end(key)\n"
                    "        return self.cache[key]\n\n"
                    "    def put(self, key, value):\n"
                    "        if key in self.cache:\n"
                    "            self.cache.move_to_end(key)\n"
                    "        self.cache[key] = value\n"
                    "        if len(self.cache) > self.cap:\n"
                    "            self.cache.popitem(last=False)\n"
                ),
            },
        },
    }

    def __init__(self, tier: ModelTier = ModelTier.WEAK):
        self.tier = tier
        self._attempt_counts: dict[str, int] = {}

    @property
    def model_name(self) -> str:
        return f"developer_{self.tier.value}"

    def generate(self, task_id: str, reviewer_hint: str = "") -> Message:
        """
        Генерирует код для задачи.
        reviewer_hint — подсказка от ревьюера (если была предыдущая итерация).
        Возвращает Message с кодом.
        """
        # Считаем попытки по этой задаче
        self._attempt_counts[task_id] = self._attempt_counts.get(task_id, 0) + 1
        attempt = self._attempt_counts[task_id]

        task_solutions = self._SOLUTIONS.get(task_id, {})
        tier_solutions = task_solutions.get(self.tier, {})

        # Берём решение для текущей попытки, или последнее доступное
        code = tier_solutions.get(attempt) or tier_solutions.get(max(tier_solutions.keys(), default=1), "# нет решения")

        return Message(
            sender=self.role,
            recipient=AgentRole.REVIEWER,
            content={
                "task_id": task_id,
                "code": code,
                "attempt": attempt,
                "tier": self.tier.value,
                "reviewer_hint": reviewer_hint,
            }
        )