from dataclasses import dataclass, field
from typing import List, Optional
from agents.base import AgentRole, ModelTier, Message, AgentMemory

# ── Возможные решения менеджера ──────────────────────────────────────────────

MANAGER_DECISIONS = {
    "send_to_review": "Отправить код на ревью",
    "send_to_test": "Отправить код на тестирование",
    "request_changes_weak": "Попросить разработчика (weak) переписать",
    "escalate_strong": "Эскалировать: заменить на сильного разработчика",
    "escalate_human": "Эскалировать: позвать человека",
    "accept": "Принять решение — задача решена",
    "stop": "Остановиться — исчерпан лимит попыток",
}


@dataclass
class ManagerPolicy:
    """
    Политика менеджера — набор правил для принятия решений.

    Это то, ЧТО оценивает твой бенчмарк:
    насколько хорошо эти правила работают в разных сценариях.

    В реальной системе политика может быть обучаемой (как в CascadeDebate),
    в прототипе — набор порогов.
    """
    # Порог pass rate: ниже него — код не принимается
    pass_threshold: float = 1.0

    # Порог quality score от ревьюера: ниже — просим переписать
    quality_threshold: float = 0.6

    # Сколько раз даём слабому разработчику шанс переписать
    max_weak_attempts: int = 2

    # Сколько раз даём сильному разработчику
    max_strong_attempts: int = 1

    # Максимум итераций всего
    max_total_iterations: int = 6


class ManagerAgent:
    """
    Агент-менеджер: принимает решения об эскалации на основе
    отчётов от ревьюера и тестировщика.
    """
    role = AgentRole.MANAGER

    def __init__(self, policy: ManagerPolicy):
        self.policy = policy
        self.memory = AgentMemory()

        # Счётчики состояния
        self._weak_attempts = 0
        self._strong_attempts = 0
        self._current_tier = ModelTier.WEAK
        self._iteration = 0

    # Основной метод принятия решений─

    def decide_after_review(self, review_msg: Message) -> tuple[str, str]:
        """
        Менеджер смотрит на заключение ревьюера и решает что делать.
        Возвращает: (решение, объяснение для лога)
        """
        self.memory.add(review_msg)
        rec = review_msg.content["recommendation"]
        quality = review_msg.content["quality_score"]
        hint = review_msg.content["hint_for_developer"]

        self._iteration += 1

        # Ревьюер рекомендует отправить на тест
        if rec == "approve":
            return "send_to_test", f"Ревьюер одобрил (quality={quality:.2f}), отправляем на тест"

        # Ревьюер рекомендует эскалацию — менеджер проверяет, согласен ли он
        if rec == "escalate":
            return self._escalation_decision(f"Ревьюер рекомендует эскалацию (quality={quality:.2f})")

        # Ревьюер просит переделать
        if rec == "request_changes":
            if self._current_tier == ModelTier.WEAK and self._weak_attempts < self.policy.max_weak_attempts:
                return "request_changes_weak", f"Ревьюер нашёл проблемы ({hint[:60]}...), даём ещё попытку"
            else:
                return self._escalation_decision(
                    f"Слабый разработчик исчерпал попытки ({self._weak_attempts}), качество={quality:.2f}")

        return "stop", "Неизвестная рекомендация от ревьюера"

    def decide_after_test(self, test_msg: Message) -> tuple[str, str]:
        """
        Менеджер смотрит на результат тестов и решает что делать.
        Возвращает: (решение, объяснение для лога)
        """
        self.memory.add(test_msg)
        pass_rate = test_msg.content["pass_rate"]
        success = test_msg.content["success"]
        failures = test_msg.content["failure_reasons"]

        # Все тесты прошли — готово!
        if success:
            return "accept", f"Все тесты прошли (pass_rate={pass_rate:.0%})"

        # Тесты не прошли — нужно что-то делать
        summary = f"pass_rate={pass_rate:.0%}, провалов: {len(failures)}"

        if self._current_tier == ModelTier.WEAK and self._weak_attempts < self.policy.max_weak_attempts:
            return "request_changes_weak", f"Тесты не прошли ({summary}), просим переработать"

        return self._escalation_decision(f"Тесты не прошли после попыток: {summary}")

    # ── Внутренняя логика эскалации ──────────────────────────────────────────

    def _escalation_decision(self, reason: str) -> tuple[str, str]:
        """Принимает конкретное решение об эскалации."""

        if self._iteration >= self.policy.max_total_iterations:
            return "stop", f"Исчерпан лимит итераций ({self._iteration})"

        # Слабый → сильный
        if self._current_tier == ModelTier.WEAK:
            self._current_tier = ModelTier.STRONG
            return "escalate_strong", f"Эскалация: слабый не справился ({reason}) → подключаем сильного разработчика"

        # Сильный не справился → человек
        if self._current_tier == ModelTier.STRONG and self._strong_attempts >= self.policy.max_strong_attempts:
            return "escalate_human", f"Эскалация: сильный не справился ({reason}) → зовём человека"

        return "escalate_strong", f"Продолжаем с сильным разработчиком ({reason})"

    # ── Обновление состояния ─────────────────────────────────────────────────

    def register_attempt(self, tier: ModelTier):
        """Вызывается каждый раз когда разработчик сделал попытку."""
        if tier == ModelTier.WEAK:
            self._weak_attempts += 1
        else:
            self._strong_attempts += 1

    @property
    def current_tier(self) -> ModelTier:
        return self._current_tier