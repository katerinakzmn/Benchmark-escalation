"""
reviewer.py — агент-ревьюер (code reviewer).

Роль: получить код от разработчика → проверить качество → дать заключение.
НЕ запускает тесты (это работа тестировщика).
Смотрит на структуру кода: есть ли обработка edge-cases, читаемость, паттерны.

В реальной системе: LLM с промптом вида
  "Ты опытный ревьюер. Вот код: {code}. Найди проблемы и дай рекомендации."

Ревьюер передаёт:
  - оценку качества кода (0.0–1.0)
  - список найденных проблем
  - конкретную подсказку для разработчика
  - рекомендацию: "переписать" / "достаточно хорошо" / "нужна сильная модель"
"""

from agents.base import AgentRole, Message


class ReviewerAgent:
    role = AgentRole.REVIEWER

    _KNOWN_ISSUES = {
        "fizzbuzz_order": {
            "pattern": lambda code: "% 3" in code and "% 15" not in code,
            "hint": "Проверь порядок условий: случай n%15 должен идти ПЕРЕД n%3 и n%5, иначе FizzBuzz никогда не вернётся.",
            "quality_penalty": 0.4,
        },
        "lru_no_orderdict": {
            "pattern": lambda code: "LRUCache" in code and "OrderedDict" not in code,
            "hint": "Для корректного LRU кэша используй collections.OrderedDict — он позволяет эффективно отслеживать порядок обращений.",
            "quality_penalty": 0.5,
        },
        "no_solution_fn": {
            "pattern": lambda code: "def solution" not in code and "class LRUCache" not in code,
            "hint": "Код не содержит ни функции solution(), ни класса LRUCache. Проверь структуру ответа.",
            "quality_penalty": 0.9,
        },
    }

    def review(self, dev_message: Message) -> Message:
        """
        Проверяет код и возвращает заключение.
        """
        code = dev_message.content.get("code", "")
        task_id = dev_message.content.get("task_id", "")

        issues = []
        total_penalty = 0.0
        hints = []

        for issue_name, issue_def in self._KNOWN_ISSUES.items():
            if issue_def["pattern"](code):
                issues.append(issue_name)
                total_penalty += issue_def["quality_penalty"]
                hints.append(issue_def["hint"])

        # Оценка качества: 1.0 = идеально, 0.0 = очень плохо
        quality_score = max(0.0, 1.0 - total_penalty)

        # Рекомендация для менеджера
        if quality_score >= 0.8:
            recommendation = "approve"          # отправить тестировщику
        elif quality_score >= 0.4:
            recommendation = "request_changes"  # попросить разработчика переписать
        else:
            recommendation = "escalate"         # ревьюер сам рекомендует эскалацию

        hint_text = " ".join(hints) if hints else "Код выглядит корректно по структуре."

        return Message(
            sender=self.role,
            recipient=AgentRole.MANAGER,
            content={
                "task_id": task_id,
                "code": code,
                "quality_score": round(quality_score, 2),
                "issues_found": issues,
                "hint_for_developer": hint_text,
                "recommendation": recommendation,
            }
        )