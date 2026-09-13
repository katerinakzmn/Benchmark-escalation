"""Optional LLM backends used by the policy runner.

The mock backend is the default for reproducible experiments. These adapters
exist so the CLI can be extended to real providers without breaking local runs
when provider SDKs or API keys are absent.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml

# Loading .env
try:
    from dotenv import load_dotenv as _load_dotenv
    _env_path = Path(__file__).resolve().parent.parent / ".env"
    _load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass

from tasks import load_tasks


_SYSTEM_PROMPT = """Return only JSON:
{
  "fixed_code": "<complete corrected Python code>",
  "confidence": <number from 0.0 to 1.0>
}
"""

# Pricing loader

_PRICING_CACHE: Optional[Dict[str, Any]] = None


def _load_pricing() -> Dict[str, Any]:
    """Load pricing config from configs/pricing.yaml (relative to repo root)."""
    global _PRICING_CACHE
    if _PRICING_CACHE is not None:
        return _PRICING_CACHE

    candidates = [
        Path(__file__).parent.parent / "configs" / "pricing.yaml",
        Path("configs") / "pricing.yaml",
        Path(__file__).parent / "configs" / "pricing.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            with open(candidate, "r", encoding="utf-8") as f:
                _PRICING_CACHE = yaml.safe_load(f)
            return _PRICING_CACHE

    # Fallback: hardcoded defaults matching pricing.yaml content
    _PRICING_CACHE = {
        "models": {
            "gpt-4o-mini": {"input_per_million": 0.15, "output_per_million": 0.60},
            "gpt-4o": {"input_per_million": 2.50, "output_per_million": 10.00},
        }
    }
    return _PRICING_CACHE


def _resolve_model_pricing(model_name: str) -> Dict[str, float]:
    """Resolve model name (including aliases) to pricing entry."""
    pricing = _load_pricing()
    models = pricing.get("models", {})

    entry = models.get(model_name, {})
    # Follow alias if present
    if "alias" in entry:
        entry = models.get(entry["alias"], {})

    return {
        "input_per_million": entry.get("input_per_million", 0.0),
        "output_per_million": entry.get("output_per_million", 0.0),
    }


def _compute_cost(model_name: str, input_tokens: int, output_tokens: int) -> Dict[str, float]:
    """Compute USD costs for a given model and token counts."""
    prices = _resolve_model_pricing(model_name)
    input_cost = (input_tokens / 1_000_000) * prices["input_per_million"]
    output_cost = (output_tokens / 1_000_000) * prices["output_per_million"]
    return {
        "input_cost_usd": round(input_cost, 9),
        "output_cost_usd": round(output_cost, 9),
        "step_cost_usd": round(input_cost + output_cost, 9),
    }




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
    def _parse_response(raw: str) -> Dict[str, Any]:
        """Parse LLM response JSON, returning fixed_code and optional confidence."""
        raw = raw.strip()
        try:
            data = json.loads(raw)
            return {
                "fixed_code": data.get("fixed_code") or data.get("code") or raw,
                "confidence": data.get("confidence"),
            }
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group())
                    return {
                        "fixed_code": data.get("fixed_code") or data.get("code") or raw,
                        "confidence": data.get("confidence"),
                    }
                except json.JSONDecodeError:
                    pass
        return {"fixed_code": _strip_code_fences(raw), "confidence": None}

    @staticmethod
    def _parse_fixed_code(raw: str) -> str:
        """Legacy helper kept for backward compatibility."""
        return _TaskLookupMixin._parse_response(raw)["fixed_code"]

    def review(self, task_id: str, code: str, tier: str = "weak") -> dict:
        return {"issues": [], "confidence": 0.5, "approved": True}


# Backends

_MOCK_FIXES: Dict[str, str] = {
    "T001": "def sum_positive(numbers):\n    return sum(x for x in numbers if x > 0)\n",
    "T002": "def count_vowels(text):\n    return sum(1 for c in text if c in 'aeiouAEIOU')\n",
    "T003": "def is_palindrome(s):\n    s = s.lower()\n    return s == s[::-1]\n",
    "T004": "def reverse_words(text):\n    return ' '.join(text.split()[::-1])\n",
    "T005": "def find_max(numbers):\n    if not numbers:\n        raise ValueError('empty list')\n    return max(numbers)\n",
    "T006": "import time\nclass TTLCache:\n    def __init__(self, ttl):\n        self.ttl = ttl\n        self.store = {}\n    def set(self, key, value):\n        self.store[key] = (value, time.time())\n    def get(self, key):\n        if key not in self.store:\n            return None\n        value, ts = self.store[key]\n        if time.time() - ts > self.ttl:\n            del self.store[key]\n            return None\n        return value\n",
    "T007": "def flatten_dict(d, parent_key=''):\n    items = {}\n    for k, v in d.items():\n        new_key = f'{parent_key}_{k}' if parent_key else k\n        if isinstance(v, dict):\n            items.update(flatten_dict(v, new_key))\n        else:\n            items[new_key] = v\n    return items\n",
    "T008": "def most_frequent(items):\n    if not items:\n        return None\n    counts = {}\n    for item in items:\n        counts[item] = counts.get(item, 0) + 1\n    return max(counts, key=counts.get)\n",
    "T009": "def chunk_list(lst, size):\n    if size <= 0:\n        raise ValueError('size > 0')\n    return [lst[i:i+size] for i in range(0, len(lst), size)]\n",
    "T010": "def normalize_scores(scores):\n    if not scores:\n        return []\n    mn, mx = min(scores), max(scores)\n    if mx == mn:\n        return [0.0 for _ in scores]\n    return [(x - mn) / (mx - mn) for x in scores]\n",
    "T011": "import time\nfrom collections import deque\nclass RateLimiter:\n    def __init__(self, max_calls, window_seconds):\n        self.max_calls = max_calls\n        self.window = window_seconds\n        self.calls = deque()\n    def is_allowed(self):\n        now = time.time()\n        cutoff = now - self.window\n        while self.calls and self.calls[0] < cutoff:\n            self.calls.popleft()\n        if len(self.calls) >= self.max_calls:\n            return False\n        self.calls.append(now)\n        return True\n",
    "T012": "from collections import OrderedDict\nclass LRUCache:\n    def __init__(self, capacity):\n        self.capacity = capacity\n        self.cache = OrderedDict()\n    def get(self, key):\n        if key not in self.cache:\n            return -1\n        self.cache.move_to_end(key)\n        return self.cache[key]\n    def put(self, key, value):\n        if key in self.cache:\n            self.cache.move_to_end(key)\n        self.cache[key] = value\n        if len(self.cache) > self.capacity:\n            self.cache.popitem(last=False)\n",
    "T013": "def merge_intervals(intervals):\n    if not intervals:\n        return []\n    intervals = sorted(intervals)\n    merged = [intervals[0]]\n    for start, end in intervals[1:]:\n        if start <= merged[-1][1]:\n            merged[-1][1] = max(merged[-1][1], end)\n        else:\n            merged.append([start, end])\n    return merged\n",
    "T014": "from collections import deque\ndef topological_sort(graph):\n    in_degree = {node: 0 for node in graph}\n    for node in graph:\n        for nei in graph[node]:\n            in_degree[nei] = in_degree.get(nei, 0) + 1\n    q = deque([n for n, d in in_degree.items() if d == 0])\n    order = []\n    while q:\n        node = q.popleft()\n        order.append(node)\n        for nei in graph.get(node, []):\n            in_degree[nei] -= 1\n            if in_degree[nei] == 0:\n                q.append(nei)\n    return order\n",
    "T015": "from collections import deque\ndef shortest_path_bfs(graph, start, goal):\n    visited = {start}\n    q = deque([(start, 0)])\n    while q:\n        node, dist = q.popleft()\n        if node == goal:\n            return dist\n        for nei in graph.get(node, []):\n            if nei not in visited:\n                visited.add(nei)\n                q.append((nei, dist + 1))\n    return -1\n",
}


class MockBackend(_TaskLookupMixin):
    """Детерминированный mock-бэкенд для воспроизводимых экспериментов.

    Возвращает dict с нулевыми токенами и нулевой стоимостью —
    так что downstream-код, ожидающий новый dict-интерфейс, работает без изменений.

    Исходы определяются таблицей _DEFAULT_SCENARIOS:
      weak=solve  → mock возвращает правильный код
      weak=fail   → mock возвращает баговый код (не пройдёт тесты)
    """

    # Сценарии: какой tier решит задачу
    _DEFAULT_SCENARIOS: Dict[str, Dict[str, bool]] = {
        "T001": {"weak": True,  "strong": True,  "human": True},
        "T002": {"weak": False, "strong": True,  "human": True},
        "T003": {"weak": False, "strong": False, "human": True},
        "T004": {"weak": False, "strong": True,  "human": True},
        "T005": {"weak": True,  "strong": True,  "human": True},
        "T006": {"weak": False, "strong": True,  "human": True},
        "T007": {"weak": False, "strong": False, "human": True},
        "T008": {"weak": True,  "strong": True,  "human": True},
        "T009": {"weak": False, "strong": True,  "human": True},
        "T010": {"weak": False, "strong": False, "human": True},
        "T011": {"weak": False, "strong": False, "human": True},
        "T012": {"weak": False, "strong": True,  "human": True},
        "T013": {"weak": False, "strong": True,  "human": True},
        "T014": {"weak": False, "strong": False, "human": True},
        "T015": {"weak": False, "strong": False, "human": True},
    }

    def __init__(self, scenarios: Optional[Dict] = None):
        super().__init__()
        self._scenarios = scenarios or self._DEFAULT_SCENARIOS

    def generate(self, task_id: str, tier: str, prompt: str = "") -> Dict[str, Any]:
        task = self._tasks.get(task_id)
        scenario = self._scenarios.get(task_id, {})
        # human tier всегда решает (правка 0.1)
        will_solve = (tier == "human") or scenario.get(tier, False)

        if will_solve and task_id in _MOCK_FIXES:
            fixed_code = _MOCK_FIXES[task_id]
        elif will_solve and task:
            # Для T016+ tasks в mock возвращаем reference_solution
            fixed_code = task.reference_solution or task.original_code
        else:
            # Намеренно возвращаем баговый код
            fixed_code = task.original_code if task else ""

        return {
            "fixed_code":      fixed_code,
            "confidence":      0.85 if will_solve else 0.35,
            "model":           f"mock-{tier}",
            "input_tokens":    0,
            "output_tokens":   0,
            "input_cost_usd":  0.0,
            "output_cost_usd": 0.0,
            "step_cost_usd":   0.0,
            "status":          "solved" if will_solve else "test_failed",
        }


class OpenAIBackend(_TaskLookupMixin):
    def __init__(self):
        super().__init__()
        self.models = {
            "weak": os.getenv("OPENAI_WEAK_MODEL", "gpt-4o-mini"),
            "strong": os.getenv("OPENAI_STRONG_MODEL", "gpt-4o"),
            "human": os.getenv("OPENAI_HUMAN_MODEL", "gpt-4o"),
        }

    def generate(self, task_id: str, tier: str, prompt: str = "") -> Dict[str, Any]:
        model_name = self.models.get(tier, self.models["weak"])

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            return {
                "fixed_code": "",
                "confidence": None,
                "model": model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd": 0.0,
                "status": "api_error",
            }

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt or self._prompt_for(task_id)},
                ],
                temperature=0.2,
            )

            raw_content = response.choices[0].message.content or ""
            parsed = self._parse_response(raw_content)

            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            costs = _compute_cost(model_name, input_tokens, output_tokens)

            result: Dict[str, Any] = {
                "fixed_code": parsed["fixed_code"],
                "model": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "status": "solved",
            }
            if parsed["confidence"] is not None:
                result["confidence"] = parsed["confidence"]
            result.update(costs)
            return result

        except Exception:
            return {
                "fixed_code": "",
                "confidence": None,
                "model": model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd": 0.0,
                "status": "api_error",
            }


class GeminiBackend(_TaskLookupMixin):
    def __init__(self):
        super().__init__()
        self.models = {
            "weak": os.getenv("GEMINI_WEAK_MODEL", "gemini-1.5-flash"),
            "strong": os.getenv("GEMINI_STRONG_MODEL", "gemini-1.5-pro"),
            "human": os.getenv("GEMINI_HUMAN_MODEL", "gemini-1.5-pro"),
        }

    def generate(self, task_id: str, tier: str, prompt: str = "") -> Dict[str, Any]:
        import google.generativeai as genai

        model_name = self.models.get(tier, self.models["weak"])

        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return {
                "fixed_code": "",
                "confidence": None,
                "model": model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd": 0.0,
                "status": "api_error",
            }

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                f"{_SYSTEM_PROMPT}\n\n{prompt or self._prompt_for(task_id)}"
            )

            raw_content = getattr(response, "text", "") or ""
            parsed = self._parse_response(raw_content)

            # Gemini usage metadata (may not always be present)
            usage = getattr(response, "usage_metadata", None)
            input_tokens = getattr(usage, "prompt_token_count", 0) or 0
            output_tokens = getattr(usage, "candidates_token_count", 0) or 0

            # Gemini pricing is not in the YAML; fall back to zero cost
            costs = {
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd": 0.0,
            }

            result: Dict[str, Any] = {
                "fixed_code": parsed["fixed_code"],
                "model": model_name,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "status": "solved",
            }
            if parsed["confidence"] is not None:
                result["confidence"] = parsed["confidence"]
            result.update(costs)
            return result

        except Exception:
            return {
                "fixed_code": "",
                "confidence": None,
                "model": model_name,
                "input_tokens": 0,
                "output_tokens": 0,
                "input_cost_usd": 0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd": 0.0,
                "status": "api_error",
            }


# Utility


def _strip_code_fences(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    if lines and lines[0].strip() == "python":
        lines = lines[1:]
    return "\n".join(lines).strip()


class PolzaBackend(_TaskLookupMixin):
    """
    Polza.ai принимает те же запросы, что и OpenAI API, но:
      - base_url = "https://polza.ai/api/v1"
      - api_key  = POLZA_API_KEY (из .env)
      - model ID содержит префикс провайдера: "openai/gpt-4o-mini"
    """

    POLZA_BASE_URL = "https://polza.ai/api/v1"

    def __init__(self):
        super().__init__()
        self.models = {
            "weak":   os.getenv("POLZA_WEAK_MODEL",   "openai/gpt-4o-mini"),
            "strong": os.getenv("POLZA_STRONG_MODEL",  "openai/gpt-4o"),
            "human":  os.getenv("POLZA_HUMAN_MODEL",   "openai/gpt-4o"),
        }

    def generate(self, task_id: str, tier: str, prompt: str = "") -> Dict[str, Any]:
        model_name = self.models.get(tier, self.models["weak"])

        api_key = os.getenv("POLZA_API_KEY")
        if not api_key:
            return {
                "fixed_code":      "",
                "confidence":      None,
                "model":           model_name,
                "input_tokens":    0,
                "output_tokens":   0,
                "input_cost_usd":  0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd":   0.0,
                "status":          "api_error",
                "error":           "POLZA_API_KEY not set. Add it to .env file.",
            }

        try:
            from openai import OpenAI

            client = OpenAI(
                base_url=self.POLZA_BASE_URL,
                api_key=api_key,
            )

            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt or self._prompt_for(task_id)},
                ],
                temperature=0.0,   # temperature=0 для воспроизводимости
                max_tokens=2048,
            )

            raw_content = response.choices[0].message.content or ""
            parsed = self._parse_response(raw_content)

            usage = response.usage
            input_tokens  = usage.prompt_tokens     if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

            # Считаем стоимость
            costs = _compute_cost(model_name, input_tokens, output_tokens)

            result: Dict[str, Any] = {
                "fixed_code":   parsed["fixed_code"],
                "model":        model_name,
                "input_tokens": input_tokens,
                "output_tokens":output_tokens,
                "status":       "solved",
            }
            if parsed["confidence"] is not None:
                result["confidence"] = parsed["confidence"]
            result.update(costs)
            return result

        except Exception as e:
            return {
                "fixed_code":      "",
                "confidence":      None,
                "model":           model_name,
                "input_tokens":    0,
                "output_tokens":   0,
                "input_cost_usd":  0.0,
                "output_cost_usd": 0.0,
                "step_cost_usd":   0.0,
                "status":          "api_error",
                "error":           str(e),
            }