"""
Единый CLI для запуска benchmark.
  # Mock-прогон (без API-ключа):
  python -m runner.run_benchmark --backend mock --policy fixed_weak

  # Реальный прогон с OpenAI:
  python -m runner.run_benchmark --backend openai --policy retry_then_escalate --config configs/real_openai.yaml

  # Только несколько задач (для теста):
  python -m runner.run_benchmark --backend openai --policy retry_then_escalate --tasks T001 T002 T003

  # Sweep всех политик:
  python -m runner.sweep --backend openai --config configs/real_openai.yaml
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
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_dir = os.path.join("runs", f"run_{timestamp}")
    os.makedirs(run_dir, exist_ok=True)
    return run_dir


def _git_commit() -> str:
    try:
        import subprocess
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def run_benchmark(args, config: dict):
    dataset_name = args.dataset or config.get("dataset", "toy")
    backend_name = args.backend or config.get("backend", "mock")
    policy_name  = args.policy  or config.get("policy", {}).get("name", "retry_then_escalate")
    policy_cfg   = {**config.get("policy", {}), "seed": config.get("seed", 42)}
    budget_cfg   = config.get("budget", {"max_total_iterations": 7})
    costs_cfg    = config.get("costs",  {"weak_call": 1, "strong_call": 3,
                                          "review_call": 1, "test_run": 0.5, "human_call": 10})

    # загрузка задач
    all_tasks = load_tasks()
    if args.tasks:
        all_tasks = [t for t in all_tasks if t.instance_id in args.tasks]
    if not all_tasks:
        print("[ERROR] No tasks found. Check dataset/tasks.json or --tasks filter.")
        sys.exit(1)

    # Фильтр по сложности
    if getattr(args, "difficulty", None):
        all_tasks = [t for t in all_tasks if t.difficulty == args.difficulty]

    # backend и policy
    backend = get_backend(backend_name)
    policy  = get_policy(policy_name, policy_cfg)

    # создаём run директорию
    run_dir = make_run_dir()
    print(f"\n{'='*55}")
    print(f"  Benchmark run : {run_dir}")
    print(f"  Backend       : {backend_name}")
    print(f"  Policy        : {policy_name}")
    print(f"  Tasks         : {len(all_tasks)}")
    print(f"  Max iter/task : {budget_cfg.get('max_total_iterations', 7)}")
    _task_limit = budget_cfg.get("max_cost_usd_per_task") or budget_cfg.get("max_cost_per_task")
    if _task_limit is not None:
        _cur = "₽" if backend_name == "polza" else "$"
        print(f"  Max cost/task : {_cur}{_task_limit:.2f}")
    print(f"{'='*55}\n")

    # --- experiment manifest ---
    manifest = {
        "timestamp":      datetime.now().isoformat(),
        "git_commit":     _git_commit(),
        "backend":        backend_name,
        "policy":         {**policy_cfg, "name": policy_name},
        "budget":         budget_cfg,
        "costs":          costs_cfg,
        "dataset":        dataset_name,
        "seed":           config.get("seed", 42),
        "task_count":     len(all_tasks),
        "tasks":          [t.instance_id for t in all_tasks],
        "models": {
            "weak":   (os.getenv("POLZA_WEAK_MODEL")
                       or os.getenv("OPENAI_WEAK_MODEL")
                       or "openai/gpt-4o-mini"),
            "strong": (os.getenv("POLZA_STRONG_MODEL")
                       or os.getenv("OPENAI_STRONG_MODEL")
                       or "openai/gpt-4o"),
        },
    }
    with open(os.path.join(run_dir, "experiment_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    with open(os.path.join(run_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    # запуск задач
    all_traces  = []
    all_metrics = []
    total_cost_usd = 0.0

    for task in all_tasks:
        print(f"  Running {task.instance_id} [{task.difficulty}] ...", end=" ", flush=True)
        result = policy.run_task(task, backend, budget_cfg, costs_cfg)
        m = result["metrics"]

        status_str = m.get("status", "solved" if m["solved"] else "test_failed")
        _cur     = "₽" if backend_name == "polza" else "$"
        cost_str = f"{_cur}{m.get('cost_usd', 0.0):.4f}" if m.get("cost_usd") else f"score={m.get('cost_score', 0)}"
        print(f"{status_str}  {cost_str}")

        all_traces.append(result["trace_record"])
        all_metrics.append(m)
        total_cost_usd += m.get("cost_usd", 0.0)

        max_total = budget_cfg.get("max_total_cost_usd", float("inf"))
        if total_cost_usd >= max_total:
            _cur_b = "₽" if backend_name == "polza" else "$"
            print(f"\n[BUDGET] Достигнут лимит {_cur_b}{max_total:.2f}. Останавливаю прогон.")
            break

    # метрики
    summary = compute_summary(all_metrics)
    summary["currency_symbol"] = "₽" if backend_name == "polza" else "$"
    print_summary(summary, policy_name=policy_name)

    with open(os.path.join(run_dir, "traces.json"), "w", encoding="utf-8") as f:
        json.dump(all_traces, f, indent=2, ensure_ascii=False)

    with open(os.path.join(run_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"per_task": all_metrics, "summary": summary},
                  f, indent=2, ensure_ascii=False)

    csv_path = os.path.join(run_dir, "results.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("task_id,difficulty,solved,status,iterations,cost_score,cost_usd,"
                "input_tokens,output_tokens,escalated_strong,escalated_human,utility\n")
        for m in all_metrics:
            f.write(
                f"{m['task_id']},{m['difficulty']},{m['solved']},"
                f"{m.get('status','?')},{m['total_iterations']},"
                f"{m['cost_score']},{m.get('cost_usd',0.0):.6f},"
                f"{m.get('total_input_tokens',0)},{m.get('total_output_tokens',0)},"
                f"{m.get('escalated_to_strong',False)},{m.get('escalated_to_human',False)},"
                f"{m.get('utility',0.0):.4f}\n"
            )

    # summary.md
    solved      = summary["solved_count"]
    total       = summary["total_tasks"]
    avg_iter    = summary["avg_iterations"]
    avg_cost    = summary["avg_cost"]
    avg_cost_usd= summary.get("avg_cost_usd", 0.0)
    utility     = summary.get("utility", 0.0)
    pct         = round(100 * solved / total) if total > 0 else 0
    cur         = summary.get("currency_symbol", "₽")  # символ валюты

    summary_lines = [
        "# Benchmark Summary\n",
        f"**Run:** `{run_dir}`  ",
        f"**Backend:** `{backend_name}`  ",
        f"**Policy:** `{policy_name}`  ",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Git:** `{_git_commit()}`\n",
        "## Results\n",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Solved | {solved}/{total} ({pct}%) |",
        f"| Avg iterations | {avg_iter:.2f} |",
        f"| Avg cost (score) | {avg_cost:.2f} |",
        f"| Avg cost | {cur}{avg_cost_usd:.4f} |",
        f"| Total cost | {cur}{summary.get('total_cost_usd', 0.0):.4f} |",
        f"| Utility | {utility:.4f} |",
        f"| Strong escalation rate | {summary['escalation_to_strong_rate']:.1%} |",
        f"| Human escalation rate | {summary['escalation_to_human_rate']:.1%} |",
        "\n## Status breakdown\n",
    ]

    status_counts = summary.get("status_counts", {})
    if status_counts:
        summary_lines += ["| Status | Count |", "|--------|-------|"]
        for s, cnt in status_counts.items():
            summary_lines.append(f"| {s} | {cnt} |")

    summary_lines += [
        "\n## Per-task results\n",
        "| Task | Difficulty | Status | Iter | Cost (USD) | Utility |",
        "|------|-----------|--------|------|------------|---------|",
    ]
    for m in all_metrics:
        summary_lines.append(
            f"| {m['task_id']} | {m['difficulty']} | {m.get('status','?')} "
            f"| {m['total_iterations']} | {cur}{m.get('cost_usd',0.0):.4f} "
            f"| {m.get('utility',0.0):.4f} |"
        )

    with open(os.path.join(run_dir, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(summary_lines))

    print(f"\n  Artifacts saved in: {run_dir}/")
    print(f"    - config.json / experiment_manifest.json")
    print(f"    - traces.json")
    print(f"    - metrics.json  (per_task + summary)")
    print(f"    - results.csv")
    print(f"    - summary.md")
    print(f"{'='*55}\n")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Benchmark escalation runner")
    parser.add_argument("--dataset",    choices=["toy"])
    parser.add_argument("--backend",    choices=["mock", "openai", "gemini", "polza"])
    parser.add_argument("--policy",
                        choices=["fixed_weak", "fixed_strong",
                                 "retry_then_escalate", "progress_heuristic",
                                 "confidence_threshold", "human_fallback",
                                 "random", "oracle"])
    parser.add_argument("--config",     default="configs/default.yaml")
    parser.add_argument("--tasks",      nargs="+", help="Run only several tasks (T001 T002 ...)")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"],
                        help="Filter by difficulty")
    args = parser.parse_args()

    config = load_config(args.config)
    run_benchmark(args, config)


if __name__ == "__main__":
    main()