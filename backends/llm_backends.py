"""Optional LLM backends used by the policy runner.

The mock backend is the default for reproducible experiments. These adapters
exist so the CLI can be extended to real providers without breaking local runs
when provider SDKs or API keys are absent.
"""

import json
import os
import re

from tasks import load_tasks


_SYSTEM_PROMPT = """Return only JSON:
{
  "fixed_code": "<complete corrected Python code>",
  "confidence": <number from 0.0 to 1.0>
}
"""


class _TaskLookupMixin:
    def __init__(self):
        self._tasks = {task.instance_id: task for task in load_tasks()}

    def _prompt_for(self, task_id: str) -> str:
        task = self._tasks[task_id]
        return (
            f"Issue:\n{task.problem_statement}\n\n"
            f"Buggy code:\n```python\n{task.original_code}\n```"
        )

    @staticmethod
    def _parse_fixed_code(raw: str) -> str:
        raw = raw.strip()
        try:
            data = json.loads(raw)
            return data.get("fixed_code") or data.get("code") or raw
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                    return data.get("fixed_code") or data.get("code") or raw
                except json.JSONDecodeError:
                    pass
        return _strip_code_fences(raw)

    def review(self, task_id: str, code: str, tier: str = "weak") -> dict:
        return {"issues": [], "confidence": 0.5, "approved": True}


class OpenAIBackend(_TaskLookupMixin):
    def __init__(self):
        super().__init__()
        self.models = {
            "weak": os.getenv("OPENAI_WEAK_MODEL", "gpt-4o-mini"),
            "strong": os.getenv("OPENAI_STRONG_MODEL", "gpt-4o"),
            "human": os.getenv("OPENAI_HUMAN_MODEL", "gpt-4o"),
        }

    def generate(self, task_id: str, tier: str, prompt: str = "") -> str:
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for backend=openai")

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.models.get(tier, self.models["weak"]),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt or self._prompt_for(task_id)},
            ],
            temperature=0.2,
        )
        return self._parse_fixed_code(response.choices[0].message.content or "")


class GeminiBackend(_TaskLookupMixin):
    def __init__(self):
        super().__init__()
        self.models = {
            "weak": os.getenv("GEMINI_WEAK_MODEL", "gemini-1.5-flash"),
            "strong": os.getenv("GEMINI_STRONG_MODEL", "gemini-1.5-pro"),
            "human": os.getenv("GEMINI_HUMAN_MODEL", "gemini-1.5-pro"),
        }

    def generate(self, task_id: str, tier: str, prompt: str = "") -> str:
        import google.generativeai as genai

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY or GOOGLE_API_KEY is required for backend=gemini")

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(self.models.get(tier, self.models["weak"]))
        response = model.generate_content(f"{_SYSTEM_PROMPT}\n\n{prompt or self._prompt_for(task_id)}")
        return self._parse_fixed_code(getattr(response, "text", "") or "")


def _strip_code_fences(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    if lines and lines[0].strip() == "python":
        lines = lines[1:]
    return "\n".join(lines).strip()