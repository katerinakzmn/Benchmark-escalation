"""
Единый CLI для запуска benchmark.

Примеры:
  python -m runner.run_benchmark --backend mock --policy fixed_weak
  python -m runner.run_benchmark --backend mock --policy retry_then_escalate --tasks T001 T002
  python -m runner.run_benchmark --backend openai --config configs/default.yaml
"""
import argparse
import json
import os
import sys
import yaml
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tasks import load_tasks
from backends import get_backend
from policies.policies import get_policy
from evaluation.metrics import compute_summary, print_summary


def load_config(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def make_run_dir() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join("runs", f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def run_benchmark(args, config: dict):
    dataset_name = args.dataset or config.get("dataset", "toy")
    backend_name = args.backend or config.get("backend", "mock")
    policy_name  = args.policy  or config.get("policy", {}).get("name", "retry_then_escalate")
    policy_cfg   = config.get("policy", {})
    budget_cfg   = config.get("budget", {"max_total_iterations": 7})
    costs_cfg    = config.get("costs",  {"weak_call": 1, "strong_call": 3,
                                          "review_call": 1, "test_run": 0.5, "human_call": 10})

    # --- загрузка задач ---
    if dataset_name != "toy":
        raise ValueError("Only the toy dataset is available in this prototype.")

    all_tasks = load_tasks()
    if args.tasks:
        all_tasks = [t for t in all_tasks if t.instance_id in args.tasks]
    if not all_tasks:
        print("[ERROR] No tasks found. Check dataset/tasks.json or --tasks filter.")
        sys.exit(1)

    # --- backend и policy ---
    backend = get_backend(backend_name)
    policy  = get_policy(policy_name, policy_cfg)

    # --- создаём run директорию ---
    run_dir = make_run_dir()
    print(f"\n{'='*50}")
    print(f"  Benchmark run: {run_dir}")
    print(f"  Backend : {backend_name}")
    print(f"  Policy  : {policy_name}")
    print(f"  Tasks   : {len(all_tasks)}")
    print(f"{'='*50}\n")

    # --- сохраняем конфиг прогона ---
    run_config = {
        "timestamp": datetime.now().isoformat(),
        "dataset": dataset_name,
        "backend": backend_name,
        "policy": {"name": policy_name, **policy_cfg},
        "budget": budget_cfg,
        "costs": costs_cfg,
        "tasks": [t.instance_id for t in all_tasks],
    }
    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(run_config, f, indent=2, ensure_ascii=False)

    # --- запуск задач ---
    all_traces  = []
    all_metrics = []

    for task in all_tasks:
        print(f"  Running {task.instance_id} [{task.difficulty}] ...", end=" ", flush=True)
        result = policy.run_task(task, backend, budget_cfg, costs_cfg)
        status = "solved" if result["metrics"]["solved"] else "failed"
        print(status)
        all_traces.append(result["trace_record"])
        all_metrics.append(result["metrics"])

    # --- метрики ---
    summary = compute_summary(all_metrics)
    print_summary(summary, policy_name=policy_name)

    # --- сохраняем traces.json ---
    with open(os.path.join(run_dir, "traces.json"), "w", encoding="utf-8") as f:
        json.dump(all_traces, f, indent=2, ensure_ascii=False)

    # --- сохраняем metrics.json (per_task + summary) ---
    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"per_task": all_metrics, "summary": summary},
                  f, indent=2, ensure_ascii=False)

    # --- summary.md ---
    solved   = summary["solved_count"]
    total    = summary["total_tasks"]
    avg_iter = summary["avg_iterations"]
    avg_cost = summary["avg_cost"]

    summary_lines = [
        "# Benchmark Summary\n",
        f"**Run:** `{run_dir}`  ",
        f"**Backend:** `{backend_name}`  ",
        f"**Policy:** `{policy_name}`  ",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n",
        "## Results\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Solved | {solved}/{total} ({100*solved//total}%) |",
        f"| Avg iterations | {avg_iter:.1f} |",
        f"| Avg cost | {avg_cost:.1f} |",
        "\n## Per-task\n",
        "| Task | Difficulty | Solved | Iterations | Cost |",
        "|------|-----------|--------|-----------|------|",
    ]
    for m in all_metrics:
        mark = "yes" if m["solved"] else "no"
        summary_lines.append(
            f"| {m['task_id']} | {m['difficulty']} | {mark} "
            f"| {m['total_iterations']} | {m['cost_score']:.1f} |"
        )

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"  Artifacts: {run_dir}/")
    print(f"{'='*50}\n")


def main():
    parser = argparse.ArgumentParser(description="Benchmark escalation runner")
    parser.add_argument("--dataset", choices=["toy"])
    parser.add_argument("--backend", choices=["mock", "openai", "gemini"])
    parser.add_argument("--policy",
                        choices=["fixed_weak", "fixed_strong",
                                 "retry_then_escalate", "progress_heuristic",
                                 "confidence_threshold", "human_fallback",
                                 "random", "oracle"])
    parser.add_argument("--config", default="configs/default.yaml")
    parser.add_argument("--tasks", nargs="+")
    args = parser.parse_args()

    config = load_config(args.config)
    run_benchmark(args, config)


if __name__ == "__main__":
    main()