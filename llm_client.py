"""
llm_client.py — обёртка над OpenAI API.

Модели:
  WEAK   = gpt-4o-mini  — дешёвый ($0.15/M input), быстрый
  STRONG = gpt-4o       — умный ($2.50/M input)
  REVIEW = gpt-4o-mini  — ревью не требует большой модели

Как получить ключ:
  1. Зайди на https://platform.openai.com/api-keys
  2. Create new secret key
  3. Создай файл benchmark/.env:
     OPENAI_API_KEY=sk-...

Стоимость одного прогона бенчмарка (3 задачи):
  ~15-20 запросов × короткие промпты ≈ $0.01-0.05 (буквально копейки)
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# ── Имена моделей ─────────────────────────────────────────────────────────────
MODEL_WEAK   = "gpt-4o-mini"   # weak developer + reviewer
MODEL_STRONG = "gpt-4o"        # strong developer
MODEL_REVIEW = "gpt-4o-mini"   # reviewer

_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Возвращает OpenAI клиент (ленивая инициализация)."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY не найден.\n"
                "Создай файл benchmark/.env с содержимым:\n"
                "  OPENAI_API_KEY=sk-..."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def chat(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """
    Вызов ChatCompletion. Возвращает текст ответа.
    Интерфейс одинаков для всех агентов — провайдер скрыт здесь.
    """
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    return response.choices[0].message.content.strip()