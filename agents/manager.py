"""
manager.py — агент-менеджер.

Pipeline:

  Developer -> Manager.decide_after_generate()
                confidence >= threshold: send to Reviewer
                cant_solve: escalate without Reviewer or Tester

  Reviewer  -> Manager.decide_after_review()
                approve: send to Tester
                request_changes: return to Developer without tests
                escalate: escalate

  Tester    -> Manager.decide_after_test()
                success: accept
                failed tests: retry or escalate
                no progress: escalate to human

ЦЕПОЧКА ЭСКАЛАЦИИ:
  1. WEAK   -> attempts exhausted or cant_solve -> ESCALATE
  2. STRONG -> attempts exhausted or cant_solve -> ESCALATE
  3. HUMAN  -> final tier
"""

from dataclasses import dataclass
from typing import List
from agents.base import AgentRole, ModelTier, Message, AgentMemory


MANAGER_DECISIONS = {
    "send_to_review":    "Отправить на ревью",
    "send_to_test":      "Отправить на тестирование",
    "request_changes":   "Вернуть разработчику — переписать",
    "escalate_strong":   "Эскалировать сильной моделью",
    "escalate_human":    "Эскалировать человеком",
    "accept":            "Принять — задача решена",
    "stop":              "Остановиться — лимит исчерпан",
}


@dataclass
class ManagerPolicy:
    """
    Параметры политики эскалации.
    Примеры политик:
      Aggressive:   max_weak_attempts=1, confidence_threshold=0.8
      Conservative: max_weak_attempts=3, confidence_threshold=0.3
      Strict:       pass_threshold=1.0
    """

    # Порог pass rate для успешного прохождения тестов
    pass_threshold: float = 1.0

    # Сколько попыток даём каждому уровню
    max_weak_attempts: int = 2
    max_strong_attempts: int = 2

    # Порог confidence ниже которого немедленная эскалация
    confidence_threshold: float = 0.3

    # Сколько итераций подряд с pass_rate=0, быстрая эскалация к human
    zero_progress_limit: int = 2

    # Жёсткий лимит итераций
    max_total_iterations: int = 8


class ManagerAgent:
    """
    Принимает решения об эскалации.
    Видит всю историю итераций.
    """

    role = AgentRole.MANAGER

    def __init__(self, policy: ManagerPolicy):
        self.policy   = policy
        self.memory   = AgentMemory()

        self._weak_attempts   = 0
        self._strong_attempts = 0
        self._current_tier    = ModelTier.WEAK
        self._iteration       = 0
        self._pass_rate_history: List[float] = []


    def decide_after_generate(self, dev_msg: Message) -> tuple[str, str]:
        """
        Manager смотрит на результат Developer до Reviewer.

        Возможные решения:
          send_to_review   — confidence OK, идём к Reviewer
          request_changes  - confidence низкий, но есть ещё попытки на этом уровне
          escalate_strong  — попытки weak исчерпаны
          escalate_human   — все уровни исчерпаны
        """
        self.memory.add(dev_msg)

        confidence = dev_msg.content.get("confidence", 1.0)
        cant_solve = dev_msg.content.get("cant_solve", False)

        self._iteration += 1

        # Лимит итераций
        if self._iteration > self.policy.max_total_iterations:
            return "stop", f"Лимит итераций ({self._iteration}) исчерпан"

        # Confidence достаточный, отправляем к Reviewer
        if confidence >= self.policy.confidence_threshold and not cant_solve:
            return (
                "send_to_review",
                f"Developer уверен (confidence={confidence:.2f}); отправляем на ревью"
            )

        # Confidence низкий
        # Проверяем есть ли ещё попытки на текущем уровне
        attempts = self._current_attempts()
        max_att  = self._current_max_attempts()

        if attempts < max_att:
            tier = self._current_tier.value
            return (
                "request_changes",
                f"Низкая уверенность (confidence={confidence:.2f}) | {tier}, "
                f"попытка {attempts}/{max_att} — повторяем без ревью"
            )

        # Попытки исчерпаны, эскалируем
        return self._escalation_decision(
            f"Developer не справляется (confidence={confidence:.2f}), "
            f"попытки исчерпаны ({attempts}/{max_att})"
        )

    def decide_after_review(self, review_msg: Message) -> tuple[str, str]:
        """
        Смотрит на заключение Reviewer.
        """
        self.memory.add(review_msg)

        rec     = review_msg.content["recommendation"]
        quality = review_msg.content["quality_score"]
        hint    = review_msg.content["hint_for_developer"]

        # Ревьюер одобрил, отправляем на тест
        if rec == "approve":
            return "send_to_test", f"Ревьюер одобрил (quality={quality:.2f}); отправляем на тест"

        # Ревьюер считает что нужна эскалация
        if rec == "escalate":
            return self._escalation_decision(
                f"Ревьюер рекомендует эскалацию (quality={quality:.2f})"
            )

        # Ревьюер просит переписать
        if rec == "request_changes":
            attempts = self._current_attempts()
            max_att  = self._current_max_attempts()

            if attempts < max_att:
                tier = self._current_tier.value
                return (
                    "request_changes",
                    f"Ревьюер: {hint[:55]}... | {tier}, попытка {attempts}/{max_att}"
                )
            return self._escalation_decision(
                f"{self._current_tier.value} исчерпал попытки по ревью "
                f"({attempts}/{max_att}), quality={quality:.2f}"
            )

        return "stop", "Неизвестная рекомендация от ревьюера"

    def decide_after_test(self, test_msg: Message) -> tuple[str, str]:
        """Смотрит на результат тестов."""
        self.memory.add(test_msg)

        pass_rate = test_msg.content["pass_rate"]
        success   = test_msg.content["success"]
        failures  = test_msg.content["failure_reasons"]

        self._pass_rate_history.append(pass_rate)

        if success:
            return "accept", "Все тесты прошли (pass_rate=100%)"

        # Детектор отсутствия прогресса
        if self._no_progress():
            return (
                "escalate_human",
                f"Эскалация к human: нет прогресса, pass_rate=0 "
                f"последние {self.policy.zero_progress_limit} итерации подряд"
            )

        summary  = f"pass_rate={pass_rate:.0%}, провалов: {len(failures)}"
        attempts = self._current_attempts()
        max_att  = self._current_max_attempts()

        if attempts < max_att:
            tier = self._current_tier.value
            return (
                "request_changes",
                f"Тесты не прошли ({summary}) | {tier}, попытка {attempts}/{max_att}"
            )

        return self._escalation_decision(
            f"Тесты не прошли, попытки исчерпаны ({summary})"
        )

    def register_attempt(self, tier: ModelTier):
        """Вызывается из runner каждый раз когда Developer делает попытку."""
        if tier == ModelTier.WEAK:
            self._weak_attempts += 1
        else:
            self._strong_attempts += 1

    @property
    def current_tier(self) -> ModelTier:
        return self._current_tier


    def _escalation_decision(self, reason: str) -> tuple[str, str]:
        """Escalation chain: weak -> strong -> human."""
        if self._iteration >= self.policy.max_total_iterations:
            return "stop", f"Лимит итераций ({self._iteration}) исчерпан"

        if self._current_tier == ModelTier.WEAK:
            self._current_tier = ModelTier.STRONG
            self._pass_rate_history.clear()
            return "escalate_strong", f"weak -> strong: {reason}"

        if self._current_tier == ModelTier.STRONG:
            return "escalate_human", f"strong -> human: {reason}"

        return "stop", f"Все уровни исчерпаны: {reason}"

    def _no_progress(self) -> bool:
        limit = self.policy.zero_progress_limit
        if len(self._pass_rate_history) < limit:
            return False
        return all(pr == 0.0 for pr in self._pass_rate_history[-limit:])

    def _current_attempts(self) -> int:
        return self._weak_attempts if self._current_tier == ModelTier.WEAK else self._strong_attempts

    def _current_max_attempts(self) -> int:
        return (
            self.policy.max_weak_attempts
            if self._current_tier == ModelTier.WEAK
            else self.policy.max_strong_attempts
        )