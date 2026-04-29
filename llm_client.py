"""
llm_client.py — обёртка над OpenAI API.

Единственное место в проекте, где знают про openai-клиент.
Все агенты вызывают только эту обёртку.

Модели:
  WEAK   = gpt-3.5-turbo   (дешевле, быстрее, чаще ошибается)
  STRONG = gpt-4o           (дороже, медленнее, точнее)
  REVIEW = gpt-4o-mini      (для ревью — баланс качества и цены)
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

# Загружаем .env если он есть рядом с этим файлом
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

# Имена моделей — меняем здесь, а не по всему коду
MODEL_WEAK   = "gpt-3.5-turbo"
MODEL_STRONG = "gpt-4o"
MODEL_REVIEW = "gpt-4o-mini"

# Глобальный клиент — создаётся один раз
_client: OpenAI | None = None


def get_client() -> OpenAI:
    """Возвращает OpenAI клиент (ленивая инициализация)."""
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY не найден. "
                "Создай файл benchmark/.env и добавь: OPENAI_API_KEY=sk-..."
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
    Простой вызов ChatCompletion.
    Возвращает текст ответа.

    temperature=0.2 — почти детерминированно, подходит для кода.
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