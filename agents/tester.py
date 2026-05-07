"""
tester.py — агент-тестировщик.

Роль: получить код → запустить тесты → сообщить pass rate и детали провалов.
Это единственный агент, который взаимодействует с Environment.

В реальной системе: агент запускает тест-сьют (pytest, unittest),
собирает stdout/stderr и формирует структурированный отчёт для менеджера.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from agents.base import AgentRole, Message
from environment import Environment


class TesterAgent:
    role = AgentRole.TESTER

    def __init__(self, env: Environment):
        self.env = env
        self._step = 0

    def test(self, code: str, model_name: str, from_role: AgentRole = AgentRole.DEVELOPER) -> Message:
        """
        Прогоняет тесты и возвращает отчёт менеджеру.
        """
        self._step += 1
        result = self.env.run(code, model_name, self._step)

        return Message(
            sender=self.role,
            recipient=AgentRole.MANAGER,
            content={
                "step": self._step,
                "model_used": model_name,
                "tests_total": result.tests_total,
                "tests_passed": result.tests_passed,
                "tests_failed": result.tests_failed,
                "pass_rate": result.pass_rate,
                "failure_reasons": result.failure_reasons,
                "success": result.success,
            }
        )