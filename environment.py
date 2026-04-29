"""
environment.py — окружение бенчмарка.

Окружение — это посредник между агентом и задачей.
Агент говорит: "вот мой код" → окружение прогоняет тесты → возвращает результат.

В реальном бенчмарке здесь был бы Docker-контейнер или sandbox.
В нашем прототипе — просто exec() с перехватом ошибок.
"""

from dataclasses import dataclass
from typing import List
from tasks import Task


@dataclass
class StepResult:
    """Результат одного шага агента."""
    step_number: int
    model_used: str          # какая модель сгенерировала код
    code_generated: str      # что агент написал
    tests_total: int         # сколько тестов всего
    tests_passed: int        # сколько прошло
    tests_failed: int        # сколько провалилось
    failure_reasons: List[str]  # почему провалились
    pass_rate: float         # доля прошедших тестов [0.0 .. 1.0]
    success: bool            # True если все тесты прошли


class Environment:

    def __init__(self, task: Task):
        self.task = task

    def run(self, code: str, model_used: str, step_number: int) -> StepResult:
        """
        Прогоняет все тесты задачи на переданном коде.
        Возвращает StepResult с детальным отчётом.
        """
        passed = 0
        failed = 0
        reasons = []

        for test_fn in self.task.tests:
            result = test_fn(code)
            if result["passed"]:
                passed += 1
            else:
                failed += 1
                reasons.append(f"[{test_fn.__name__}] {result['reason']}")

        total = len(self.task.tests)
        pass_rate = passed / total if total > 0 else 0.0

        return StepResult(
            step_number=step_number,
            model_used=model_used,
            code_generated=code,
            tests_total=total,
            tests_passed=passed,
            tests_failed=failed,
            failure_reasons=reasons,
            pass_rate=pass_rate,
            success=(failed == 0),
        )