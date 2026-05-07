"""
llm_client.py — обёртка над Gemini API.

Модели:
  WEAK   = gemini-2.0-flash   (500 RPD)
  STRONG = gemini-2.5-pro     (100 RPD)
  REVIEW = gemini-2.0-flash

"""

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Загружаем .env если он есть рядом с этим файлом
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

MODEL_WEAK   = "gemini-2.0-flash"     # weak developer + reviewer
MODEL_STRONG = "gemini-2.5-pro"       # strong developer
MODEL_REVIEW = "gemini-2.0-flash"     # reviewer

# Флаг инициализации
_initialized = False


def _ensure_init():
    """Инициализирует Gemini API один раз при первом вызове."""
    global _initialized
    if _initialized:
        return

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY не найден.")
    genai.configure(api_key=api_key)
    _initialized = True


def chat(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    """
    Простой вызов Gemini.
    Возвращает текст ответа.
    temperature=0.2 — почти детерминированно, подходит для кода.
    """
    _ensure_init()

    gemini_model = genai.GenerativeModel(
        model_name=model,
        system_instruction=system_prompt,
        generation_config=genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=max_tokens,
        ),
    )

    response = gemini_model.generate_content(user_prompt)
    return response.text.strip()