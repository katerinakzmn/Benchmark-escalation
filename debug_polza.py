"""
Диагностика подключения к Polza.ai.
"""
import os
import sys
from pathlib import Path

# Загружаем .env
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    loaded = load_dotenv(dotenv_path=env_path, verbose=True)
    print(f"[1] .env файл найден и загружен: {loaded} (путь: {env_path})")
except ImportError:
    print("[1] python-dotenv не установлен! Запусти: pip install python-dotenv")
    sys.exit(1)

# Проверяем ключ
api_key = os.getenv("POLZA_API_KEY")
if not api_key:
    print("[2]  POLZA_API_KEY не найден!")

    sys.exit(1)
else:
    masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
    print(f"[2]  POLZA_API_KEY найден: {masked}")

# Проверяем openai пакет
try:
    from openai import OpenAI
    print("[3]  openai пакет установлен")
except ImportError:
    print("[3]  openai не установлен!")
    sys.exit(1)

# Тестовый запрос к Polza.ai
print("[4] Отправляем тестовый запрос к Polza.ai...")
try:
    client = OpenAI(
        base_url="https://polza.ai/api/v1",
        api_key=api_key,
    )
    response = client.chat.completions.create(
        model="openai/gpt-4o-mini",
        messages=[
            {"role": "user", "content": 'Ответь только словом "ok"'},
        ],
        max_tokens=5,
        temperature=0,
    )
    answer = response.choices[0].message.content
    print(f"[4] Ответ от Polza.ai: {answer!r}")
    print()
    print("=" * 50)
    print("Всё работает!")
except Exception as e:
    print(f"[4] Ошибка запроса: {e}")
