"""
developer.py — агент-разработчик.

Роль: получить issue + оригинальный код → исправить баг → вернуть исправленный код.

confidence (уверенность):
  Developer возвращает не только код, но и оценку уверенности 0.0–1.0.
"""

import json
import re
from agents.base import AgentRole, ModelTier, Message
from llm_client import chat, MODEL_WEAK, MODEL_STRONG


# ── Системный промпт ────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """\
Ты опытный Python-разработчик. Тебе дают:
1. Описание бага (issue)
2. Код с багом

Твоя задача: исправить баг и вернуть ответ СТРОГО в формате JSON:
{
  "fixed_code": "<исправленный Python-код>",
  "confidence": <число от 0.0 до 1.0>
}

Правила для confidence:
  1.0  — ты абсолютно уверен что исправление правильное
  0.7  — уверен, но есть небольшие сомнения
  0.5  — не уверен, решение может быть неверным
  0.3  — задача сложная, решение скорее всего неверное
  0.0  — задача непосильна для тебя

Верни ТОЛЬКО JSON без объяснений и markdown.
В поле fixed_code используй \\n для переносов строк.
"""


class DeveloperAgent:
    """
    Агент-разработчик.
      WEAK:   gemini-2.0-flash
      STRONG: gemini-2.5-pro
    """

    role = AgentRole.DEVELOPER

    def __init__(self, tier: ModelTier = ModelTier.WEAK):
        self.tier = tier
        self._attempt_counts: dict[str, int] = {}

    @property
    def model_name(self) -> str:
        return MODEL_WEAK if self.tier == ModelTier.WEAK else MODEL_STRONG

    def generate(
        self,
        task_id: str,
        issue_text: str,
        original_code: str,
        reviewer_hint: str = "",
    ) -> Message:
        """
        Генерирует исправление кода через LLM + оценку уверенности.

        Возвращает Message с полями:
          code        — исправленный код
          confidence  — уверенность модели (0.0–1.0)
          cant_solve  — True если confidence < 0.3 (модель считает задачу непосильной)
        """
        self._attempt_counts[task_id] = self._attempt_counts.get(task_id, 0) + 1
        attempt = self._attempt_counts[task_id]

        user_prompt = (
            f"## Issue\n{issue_text}\n\n"
            f"## Код с багом\n```python\n{original_code}\n```"
        )

        # Если ревьюер дал подсказку — добавляем, она помогает переработать решение
        if reviewer_hint:
            user_prompt += f"\n\n## Замечания ревьюера (учти при исправлении)\n{reviewer_hint}"

        raw = chat(
            model=self.model_name,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
        )

        # Парсим JSON-ответ
        code, confidence = _parse_developer_response(raw)

        return Message(
            sender=self.role,
            recipient=AgentRole.MANAGER,   # идёт к Manager, не сразу к Reviewer
            content={
                "task_id":       task_id,
                "code":          code,
                "confidence":    confidence,
                "cant_solve":    confidence < 0.3,   # флаг "не потяну"
                "attempt":       attempt,
                "tier":          self.tier.value,
                "reviewer_hint": reviewer_hint,
            }
        )


def _parse_developer_response(raw: str) -> tuple[str, float]:
    """
    Парсит JSON-ответ разработчика.
    """
    # Убираем markdown-обёртку если есть
    raw = raw.strip()

    try:
        data = json.loads(raw)
        code       = data.get("fixed_code", "")
        confidence = float(data.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))  # зажимаем в [0,1]

        # Убираем экранированные переносы если модель их добавила
        code = code.replace("\\n", "\n").strip()
        return code, confidence

    except (json.JSONDecodeError, ValueError):
        pass

    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group())
            code       = data.get("fixed_code", "").replace("\\n", "\n").strip()
            confidence = float(data.get("confidence", 0.5))
            return code, max(0.0, min(1.0, confidence))
        except (json.JSONDecodeError, ValueError):
            pass
    code = _strip_code_fences(raw)
    return code, 0.5


def _strip_code_fences(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()