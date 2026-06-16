"""
reviewer.py — агент-ревьюер.

Роль: получить оригинальный код + исправленный код → провести ревью → дать заключение.

Использует LLM с промптом, который возвращает
структурированный JSON-ответ.

Структура ответа:
  quality_score:     float 0.0–1.0
  issues_found:      list[str]  — краткие названия проблем
  hint_for_developer: str        — конкретная подсказка что исправить
  recommendation:    "approve" | "request_changes" | "escalate"
"""

import json
import re
from agents.base import AgentRole, Message
from backends.llm_client import chat, MODEL_REVIEW


_SYSTEM_PROMPT = """\
Ты опытный ревьюер Python-кода. Тебе дают:
1. Оригинальный код с багом
2. Исправленный код от разработчика
3. Описание issue (что нужно было исправить)

Оцени качество исправления и верни ответ СТРОГО в формате JSON:
{
  "quality_score": <число от 0.0 до 1.0>,
  "issues_found": ["краткое название проблемы 1", ...],
  "hint_for_developer": "конкретная подсказка что именно исправить",
  "recommendation": "approve" | "request_changes" | "escalate"
}

Правила для recommendation:
  "approve"         — исправление правильное, можно запускать тесты (quality_score >= 0.8)
  "request_changes" — есть ошибки, но разработчик может исправить сам (0.4 <= quality_score < 0.8)
  "escalate"        — задача слишком сложная для текущей модели (quality_score < 0.4)

Верни ТОЛЬКО JSON без объяснений и markdown.
"""


class ReviewerAgent:
    role = AgentRole.REVIEWER

    def review(self, dev_message: Message) -> Message:
        """
        Проверяет исправленный код через LLM и возвращает заключение.
        """
        code        = dev_message.content.get("code", "")
        task_id     = dev_message.content.get("task_id", "")

        # Получаем оригинальный код и issue из контекста сообщения
        original_code = dev_message.content.get("original_code", "")
        issue_text    = dev_message.content.get("issue_text", "")

        user_prompt = (
            f"## Issue\n{issue_text}\n\n"
            f"## Оригинальный код (с багом)\n```python\n{original_code}\n```\n\n"
            f"## Исправленный код от разработчика\n```python\n{code}\n```"
        )

        raw = chat(
            model=MODEL_REVIEW,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,   # ревью должно быть стабильным
        )

        # Парсим JSON
        parsed = _parse_review_json(raw)

        return Message(
            sender=self.role,
            recipient=AgentRole.MANAGER,
            content={
                "task_id":            task_id,
                "code":               code,
                "quality_score":      parsed["quality_score"],
                "issues_found":       parsed["issues_found"],
                "hint_for_developer": parsed["hint_for_developer"],
                "recommendation":     parsed["recommendation"],
                "raw_response":       raw,   # сохраняем для логов
            }
        )


def _parse_review_json(raw: str) -> dict:
    """
    Парсит JSON-ответ ревьюера.
    Если LLM всё-таки добавил markdown — вырезаем JSON из текста.
    Если что-то пошло не так — возвращаем безопасные дефолты.
    """
    try:
        # Пробуем прямой парсинг
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Пробуем вытащить JSON из markdown-блока или из текста
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass

    # Полный фолбэк — что-то пошло совсем не так
    return {
        "quality_score":      0.5,
        "issues_found":       ["не удалось распарсить ответ ревьюера"],
        "hint_for_developer": "Ревьюер не смог дать структурированный ответ. Попробуй переписать решение.",
        "recommendation":     "request_changes",
    }