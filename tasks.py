"""
tasks.py — набор задач для бенчмарка.

Каждая задача — это:
  - описание на естественном языке (что нужно сделать)
  - набор тестов (функции, которые проверяют решение)
  - сложность (easy / medium / hard)
  - "правильная точка эскалации" (оракул) — нужна для метрик

Мы имитируем ситуацию из разработки сервисов:
агент получает задачу по кодированию, пишет код, тесты прогоняются.
"""

from dataclasses import dataclass, field
from typing import Callable, List


@dataclass
class Task:
    task_id: str
    description: str               # что нужно написать
    difficulty: str                # easy / medium / hard
    tests: List[Callable]          # список тест-функций
    # Оракул: на каком шаге "разумный" агент должен был эскалировать
    # None = эскалация не нужна (слабая модель должна справиться)
    oracle_escalation_step: int | None = None


def make_tasks() -> List[Task]:

    # ЗАДАЧА 1: Функция должна складывать два числа
    def test_sum_positive(solution_code: str) -> dict:
        namespace = {}
        try:
            exec(solution_code, namespace)
            fn = namespace.get("solution")
            if fn is None:
                return {"passed": False, "reason": "функция solution не найдена"}
            assert fn(2, 3) == 5
            assert fn(0, 0) == 0
            assert fn(-1, 1) == 0
            return {"passed": True, "reason": "ok"}
        except AssertionError as e:
            return {"passed": False, "reason": f"тест не прошёл: {e}"}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка выполнения: {e}"}

    task1 = Task(
        task_id="T001",
        description="Напиши функцию solution(a, b), которая возвращает сумму двух чисел.",
        difficulty="easy",
        tests=[test_sum_positive],
        oracle_escalation_step=None,
    )


    # ЗАДАЧА 2: Напиши функцию solution(n): возвращает 'Fizz' если n делится на 3
    def test_fizzbuzz_basic(solution_code: str) -> dict:
        namespace = {}
        try:
            exec(solution_code, namespace)
            fn = namespace.get("solution")
            if fn is None:
                return {"passed": False, "reason": "функция solution не найдена"}
            assert fn(3) == "Fizz"
            assert fn(5) == "Buzz"
            assert fn(15) == "FizzBuzz"
            assert fn(7) == "7"
            return {"passed": True, "reason": "ok"}
        except AssertionError:
            return {"passed": False, "reason": "неверный результат FizzBuzz"}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка: {e}"}

    def test_fizzbuzz_edge(solution_code: str) -> dict:
        namespace = {}
        try:
            exec(solution_code, namespace)
            fn = namespace.get("solution")
            if fn is None:
                return {"passed": False, "reason": "функция solution не найдена"}
            assert fn(30) == "FizzBuzz"
            assert fn(1) == "1"
            return {"passed": True, "reason": "ok"}
        except AssertionError:
            return {"passed": False, "reason": "edge-case не прошёл"}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка: {e}"}

    task2 = Task(
        task_id="T002",
        description=(
            "Напиши функцию solution(n): возвращает 'Fizz' если n делится на 3, "
            "'Buzz' если на 5, 'FizzBuzz' если на 15, иначе строку из числа."
        ),
        difficulty="medium",
        tests=[test_fizzbuzz_basic, test_fizzbuzz_edge],
        oracle_escalation_step=1,
    )

    # ЗАДАЧА 3: Реализуй класс LRUCache(capacity) с методами
    def test_lru_basic(solution_code: str) -> dict:
        namespace = {}
        try:
            exec(solution_code, namespace)
            LRUCache = namespace.get("LRUCache")
            if LRUCache is None:
                return {"passed": False, "reason": "класс LRUCache не найден"}
            cache = LRUCache(2)
            cache.put(1, 1)
            cache.put(2, 2)
            assert cache.get(1) == 1
            cache.put(3, 3)          # вытесняет ключ 2
            assert cache.get(2) == -1
            assert cache.get(3) == 3
            return {"passed": True, "reason": "ok"}
        except AssertionError:
            return {"passed": False, "reason": "LRU логика неверна"}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка: {e}"}

    def test_lru_capacity_one(solution_code: str) -> dict:
        namespace = {}
        try:
            exec(solution_code, namespace)
            LRUCache = namespace.get("LRUCache")
            if LRUCache is None:
                return {"passed": False, "reason": "класс LRUCache не найден"}
            cache = LRUCache(1)
            cache.put(1, 1)
            cache.put(2, 2)
            assert cache.get(1) == -1
            assert cache.get(2) == 2
            return {"passed": True, "reason": "ok"}
        except AssertionError:
            return {"passed": False, "reason": "capacity=1 не работает"}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка: {e}"}

    task3 = Task(
        task_id="T003",
        description=(
            "Реализуй класс LRUCache(capacity) с методами:\n"
            "  get(key) -> int  (возвращает -1 если ключ отсутствует)\n"
            "  put(key, value)  (если кэш полон — вытесняет наименее используемый ключ)"
        ),
        difficulty="hard",
        tests=[test_lru_basic, test_lru_capacity_one],
        oracle_escalation_step=1,
    )

    return [task1, task2, task3]