"""
runner/sweep.py — прогон всех политик и генерация reports/baselines.md

Пример:
  python -m runner.sweep --backend mock
  python -m runner.sweep --backend mock --tasks T001 T002 T003
"""
import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks import load_tasks
from backends import get_backend
from policies.policies import get_policy
from evaluation.metrics import compute_summary

POLICIES = [
    "fixed_weak",
    "fixed_strong",
    "retry_then_escalate",
    "progress_heuristic",
    "confidence_threshold",
    "human_fallback",
    "random",
    "oracle",
]

DEFAULT_BUDGET = {"max_total_iterations": 7}
DEFAULT_COSTS  = {"weak_call": 1, "strong_call": 3,
                  "review_call": 1, "test_run": 0.5, "human_call": 10}
DEFAULT_POLICY_CFG = {
    "max_weak_attempts": 2,
    "max_strong_attempts": 1,
    "confidence_threshold": 0.30,
    "zero_progress_limit": 2,
}


def run_sweep(backend_name: str, task_ids: list = None) -> dict:
    all_tasks = load_tasks()
    if task_ids:
        all_tasks = [t for t in all_tasks if t.task_id in task_ids]

    backend = get_backend(backend_name)
    results = {}

    for policy_name in POLICIES:
        print(f"  [{policy_name}] ...", end=" ", flush=True)
        policy = get_policy(policy_name, DEFAULT_POLICY_CFG)
        metrics_list = []

        for task in all_tasks:
            result = policy.run_task(task, backend, DEFAULT_BUDGET, DEFAULT_COSTS)
            metrics_list.append(result["metrics"])

        summary = compute_summary(metrics_list)
        results[policy_name] = summary
        solved = summary["solved_count"]
        total  = summary["total_tasks"]
        print(f"solved {solved}/{total}  cost={summary['avg_cost']:.1f}")

    return results


def build_report(results: dict, backend_name: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# Baseline Policy Comparison\n",
        f"**Date:** {date}  ",
        f"**Backend:** `{backend_name}`  ",
        f"**Tasks:** {next(iter(results.values()))['total_tasks']}\n",
        "## Results\n",
        "| Policy | Solved | Solved% | Avg Cost | Avg Iters | Escal to Strong | Escal to Human |",
        "|--------|--------|---------|----------|-----------|-------------|------------|",
    ]

    for policy_name, s in results.items():
        solved_pct = f"{s['solved_rate']*100:.0f}%"
        lines.append(
            f"| `{policy_name}` "
            f"| {s['solved_count']}/{s['total_tasks']} "
            f"| {solved_pct} "
            f"| {s['avg_cost']:.1f} "
            f"| {s['avg_iterations']:.1f} "
            f"| {s['escalation_to_strong_rate']*100:.0f}% "
            f"| {s['escalation_to_human_rate']*100:.0f}% |"
        )

    # breakdown по сложности для лучшей политики
    best = max(results, key=lambda k: results[k]["solved_rate"])
    lines += [
        f"\n## Best Policy: `{best}`\n",
        "| Difficulty | Count | Solved | Solved% | Avg Cost | Avg Iters |",
        "|------------|-------|--------|---------|----------|-----------|",
    ]
    for diff, bd in results[best].get("by_difficulty", {}).items():
        lines.append(
            f"| {diff} | {bd['count']} | {bd['solved']} "
            f"| {bd['solved_rate']*100:.0f}% "
            f"| {bd['avg_cost']:.1f} | {bd['avg_iters']:.1f} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Sweep all policies")
    parser.add_argument("--backend", choices=["mock", "openai", "gemini"],
                        default="mock")
    parser.add_argument("--tasks", nargs="+",
                        help="Ограничить задачи, напр. --tasks T001 T002")
    args = parser.parse_args()

    print(f"\n{'='*50}")
    print(f"  Sweep: {len(POLICIES)} policies × backend={args.backend}")
    print(f"{'='*50}\n")

    results = run_sweep(args.backend, args.tasks)

    # сохраняем reports/
    os.makedirs("reports", exist_ok=True)

    report_md = build_report(results, args.backend)
    report_path = os.path.join("reports", "baselines.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    results_path = os.path.join("reports", "baselines.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"  Report: {report_path}")
    print(f"  JSON  : {results_path}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()