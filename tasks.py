"""Utilities for loading benchmark tasks from ``dataset/tasks.json``.

The loader keeps compatibility with the original multi-agent runner
(``task_id``) and the newer policy runner (``instance_id``).
"""

import json
import os
from dataclasses import dataclass
from typing import Callable, List


_DATASET_PATH = os.path.join(os.path.dirname(__file__), "dataset", "tasks.json")


@dataclass
class Task:
    task_id: str
    issue_text: str
    original_code: str
    difficulty: str
    tests: List[Callable]
    task_type: str = "bug_fix"
    entry_point: str = ""
    reference_solution: str = ""
    oracle_label: str = ""

    @property
    def instance_id(self) -> str:
        return self.task_id

    @property
    def problem_statement(self) -> str:
        return self.issue_text


def make_tasks(dataset_path: str = _DATASET_PATH) -> List[Task]:
    """Load tasks from a JSON dataset file."""
    with open(dataset_path, encoding="utf-8") as f:
        records = json.load(f)

    tasks = []
    for rec in records:
        test_fns = [_build_test_fn(t) for t in rec["tests"]]
        tasks.append(Task(
            task_id       = rec["instance_id"],
            issue_text    = rec["problem_statement"],
            original_code = rec["original_code"],
            difficulty    = rec["difficulty"],
            tests         = test_fns,
            task_type     = rec.get("task_type", "bug_fix"),
            entry_point   = rec.get("entry_point", _infer_entry_point(rec["original_code"])),
            reference_solution = rec.get("reference_solution", ""),
            oracle_label  = rec.get("oracle_label", ""),
        ))
    return tasks


def load_tasks(dataset_path: str = _DATASET_PATH) -> List[Task]:
    """Alias used by the newer CLI runner."""
    return make_tasks(dataset_path)


def _build_test_fn(test_spec: dict) -> Callable:
    """Build a Python test function from a JSON test specification."""
    test_name = test_spec.get("name", "unnamed_test")
    desc      = test_spec.get("description", "")

    lines = []
    for a in test_spec.get("assertions", []):
        if a.get("custom"):
            lines.append(a["code"])

    full_test_code = "\n".join(lines)

    def test_fn(solution_code: str) -> dict:
        safe_builtins = {
            "__build_class__": __build_class__,
            "__import__": __import__,
            "abs": abs,
            "bool": bool,
            "dict": dict,
            "enumerate": enumerate,
            "Exception": Exception,
            "float": float,
            "int": int,
            "isinstance": isinstance,
            "len": len,
            "list": list,
            "max": max,
            "min": min,
            "object": object,
            "print": print,
            "range": range,
            "set": set,
            "sorted": sorted,
            "str": str,
            "sum": sum,
            "tuple": tuple,
            "ValueError": ValueError,
            "zip": zip,
        }
        ns = {"__builtins__": safe_builtins, "__name__": "__benchmark_case__"}
        try:
            exec(solution_code, ns)
            exec(full_test_code, ns)
            return {"passed": True, "reason": "ok"}
        except AssertionError as e:
            return {"passed": False, "reason": str(e)}
        except Exception as e:
            return {"passed": False, "reason": f"ошибка выполнения: {e}"}
        
    test_fn.__name__ = test_name
    test_fn.__doc__  = desc
    return test_fn


def _infer_entry_point(code: str) -> str:
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("def "):
            return stripped.split("def ", 1)[1].split("(", 1)[0]
        if stripped.startswith("class "):
            return stripped.split("class ", 1)[1].split("(", 1)[0].split(":", 1)[0]
    return ""