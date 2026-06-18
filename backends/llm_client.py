"""
llm_client.py — legacy chat client for the original MAS runner.

Backend through the LLM_BACKEND environment variable:
  LLM_BACKEND=mock    - no API key, useful for local checks
  LLM_BACKEND=openai  - OpenAI provider, used by default

If OPENAI_API_KEY is missing, the client falls back to mock.
"""

import os
import json
import random
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../.env"))

MODEL_WEAK   = "gpt-4o-mini"
MODEL_STRONG = "gpt-4o"
MODEL_REVIEW = "gpt-4o-mini"

_BACKEND = os.getenv("LLM_BACKEND", "openai").lower()

_client = None


def get_client():
    global _client
    if _client is None:
        from openai import OpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY не найден.\n"
                "Используй mock: LLM_BACKEND=mock python mas_runner.py"
            )
        _client = OpenAI(api_key=api_key)
    return _client


_MOCK_CODE = "def solution(nums):\n    return sorted(nums)\n"


def _mock_chat(model: str, system_prompt: str, user_prompt: str) -> str:
    sp = system_prompt.lower()

    if "developer" in sp or "код" in sp or "исправ" in sp:
        confidence = 0.80 if model == MODEL_STRONG else 0.55
        confidence += random.uniform(-0.05, 0.05)
        return json.dumps({
            "fixed_code":  _MOCK_CODE,
            "confidence":  round(confidence, 2),
            "cant_solve":  False,
            "explanation": "Mock developer response.",
            "attempt":     1,
        }, ensure_ascii=False)

    if "review" in sp or "ревью" in sp or "качеств" in sp:
        return json.dumps({
            "quality_score":      0.65,
            "issues_found":       ["mock_minor_issue"],
            "recommendation":     "approve",
            "hint_for_developer": "Mock reviewer: looks mostly fine.",
        }, ensure_ascii=False)

    return json.dumps({"result": "mock"})


def chat(
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
) -> str:
    backend = _BACKEND

    if backend == "openai" and not os.getenv("OPENAI_API_KEY"):
        print("[llm_client] OPENAI_API_KEY is missing; using mock backend")
        backend = "mock"

    if backend == "mock":
        return _mock_chat(model, system_prompt, user_prompt)

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