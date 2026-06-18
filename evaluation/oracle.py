"""
oracle.py - офлайн вычисление оракула для бенчмарка.

"Когда нужно было эскалировать?"
  oracle_label:
    "no_escalation" - weak справилась сама
    "escalate" - weak не справилась, strong справилась
    "unsolvable" - ни weak, ни strong не справились
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks import load_tasks
from environments.environment import Environment
from agents.developer import DeveloperAgent
from agents.base import ModelTier


_OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "../dataset", "oracle_labels.json")


def run_single_attempt(task, tier: ModelTier) -> dict:
    """
    Делает одну попытку решить задачу моделью данного уровня.
    Возвращает словарь с результатом.
    """
    dev = DeveloperAgent(tier=tier)
    env = Environment(task)

    msg = dev.generate(
        task_id       = task.task_id,
        issue_text    = task.issue_text,
        original_code = task.original_code,
    )
    code = msg.content["code"]

    result = env.run(code, model_used=tier.value, step_number=1)

    return {
        "tier":        tier.value,
        "pass_rate":   result.pass_rate,
        "success":     result.success,
        "confidence":  msg.content["confidence"],
    }


def compute_oracle_for_task(task) -> dict:
    """
    Прогоняет задачу на обеих моделях и вычисляет метку оракула.
    """
    print(f"  Задача {task.task_id} ({task.difficulty})...")

    print("    weak tier...", end=" ", flush=True)
    weak_result = run_single_attempt(task, ModelTier.WEAK)
    print(f"pass_rate={weak_result['pass_rate']:.0%}")

    print("    strong tier...", end=" ", flush=True)
    strong_result = run_single_attempt(task, ModelTier.STRONG)
    print(f"pass_rate={strong_result['pass_rate']:.0%}")

    if weak_result["success"]:
        oracle_label = "no_escalation"
    elif strong_result["success"]:
        oracle_label = "escalate"
    else:
        oracle_label = "unsolvable"

    return {
        "instance_id":    task.task_id,
        "difficulty":     task.difficulty,
        "oracle_label":   oracle_label,
        "weak_pass_rate": weak_result["pass_rate"],
        "strong_pass_rate": strong_result["pass_rate"],
        "weak_confidence":   weak_result["confidence"],
        "strong_confidence": strong_result["confidence"],
    }


if __name__ == "__main__":
    tasks = load_tasks()

    print("=" * 60)
    print("  Вычисляем оракул для бенчмарка...")
    print("  (это тратит ~2 API-вызова на задачу)")
    print("=" * 60)

    labels = []
    for task in tasks:
        label = compute_oracle_for_task(task)
        labels.append(label)
        print(f"    oracle_label: {label['oracle_label']}")
        print()

    with open(_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(labels, f, ensure_ascii=False, indent=2)

    print("=" * 60)
    print(f"  Результат сохранён в dataset/oracle_labels.json")
    print()
    print(f"  {'Задача':<8} {'Сложность':<10} {'Оракул':<16} {'Weak%':<8} {'Strong%'}")
    print("-" * 55)
    for l in labels:
        print(f"  {l['instance_id']:<8} {l['difficulty']:<10} "
              f"{l['oracle_label']:<16} {l['weak_pass_rate']:<8.0%} {l['strong_pass_rate']:.0%}")
    print("=" * 60)