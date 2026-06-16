"""
tasks.py — загрузчик задач бенчмарка.

Структура JSON-записи:
  instance_id          — уникальный ID (аналог SWE-bench instance_id)
  difficulty           — easy / medium / hard
  problem_statement    — текст issue (аналог SWE-bench problem_statement)
  original_code        — код с багом (аналог base_commit + repo)
  tests[]              — тесты для проверки исправления
    name               — имя теста
    description        — что проверяет
    assertions[]       — список assert'ов
      custom: true     — тест задан как произвольный Python-код в поле "code"
      call/expected    — простая форма: вызов и ожидаемый результат
"""

import json
import os
from dataclasses import dataclass
from typing import Callable, List


_DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset", "tasks.json")


@dataclass
class Task:
    task_id: str
    issue_text: str        # problem_statement из JSON
    original_code: str     # код с багом
    difficulty: str        # easy / medium / hard
    tests: List[Callable]  # список функций-тестов, генерируются из JSON


def make_tasks(dataset_path: str = _DATASET_PATH) -> List[Task]:
    """Загружает задачи из JSON-датасета."""
    with open(dataset_path, encoding="utf-8") as f:
        records = json.load(f)

    tasks = []
    for rec in records:
        test_fns = [_build_test_fn(t) for t in rec["tests"]]
        tasks.append(Task(
            task_id       = rec["instance_id"],
            issue_text    = rec["problem_statement"],
            original_code = rec["original_code"],
            difficulty    = rec["difficulty"],
            tests         = test_fns,
        ))
    return tasks


def _build_test_fn(test_spec: dict) -> Callable:
    """
    Строит Python-функцию теста из JSON-спецификации.
    Каждый assertion — это произвольный Python-код (custom: true).
    """
    test_name = test_spec.get("name", "unnamed_test")
    desc      = test_spec.get("description", "")

    # Собираем все assertion'ы в одно тело теста
    lines = []
    for a in test_spec.get("assertions", []):
        if a.get("custom"):
            lines.append(a["code"])

    full_test_code = "\n".join(lines)

    def test_fn(solution_code: str) -> dict:
        # ограничиваем доступные builtins
        ns = {"__builtins__": {"__import__": __import__, "len": len,
                               "range": range, "print": print,
                               "isinstance": isinstance, "type": type,
                               "int": int, "str": str, "list": list,
                               "dict": dict, "set": set, "sorted": sorted,
                               "enumerate": enumerate, "zip": zip}}
        try:
            exec(solution_code, ns)
            exec(full_test_code, ns)
            return {"passed": True, "reason": "ok"}
        except AssertionError as e:
            return {"passed": False, "reason": str(e)}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка выполнения: {e}"}
        
    test_fn.__name__ = test_name
    test_fn.__doc__  = desc
    return test_fn