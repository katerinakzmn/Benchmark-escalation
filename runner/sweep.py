"""
sweep.py  запускает все политики подряд и сохраняет сводную таблицу сравнения.

  # Mock sweep (без API, для проверки логики):
  python -m runner.sweep --backend mock

  # Реальный sweep:
  python -m runner.sweep --backend openai --config configs/real_openai.yaml

  # Pilot: только 20 первых задач, 6 политик:
  python -m runner.sweep --backend openai --config configs/real_openai.yaml --max-tasks 20

  # Только основные политики без sanity-checks:
  python -m runner.sweep --backend openai --policies fixed_weak fixed_strong retry_then_escalate
"""

import argparse
import json
import os
import sys
import yaml
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from runner.run_benchmark import run_benchmark, load_config, _git_commit

_ALL_POLICIES = [
    "fixed_weak",
    "fixed_strong",
    "retry_then_escalate",
    "confidence_threshold",
    "progress_heuristic",
    "oracle",
]


def main():
    parser = argparse.ArgumentParser(description="Sweep all escalation policies")
    parser.add_argument("--backend",    choices=["mock", "openai", "gemini", "polza"], default="mock")
    parser.add_argument("--config",     default="configs/default.yaml")
    parser.add_argument("--policies",   nargs="+", choices=_ALL_POLICIES,
                        default=_ALL_POLICIES,
                        help="Список политик для прогона (по умолчанию — все 8)")
    parser.add_argument("--tasks",      nargs="+",
                        help="Запустить только указанные задачи")
    parser.add_argument("--max-tasks",  type=int, default=None,
                        help="Ограничить число задач (pilot mode)")
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"],
                        help="Фильтровать задачи по сложности")
    args = parser.parse_args()

    config = load_config(args.config)
    sweep_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    sweep_dir = os.path.join("runs", f"sweep_{sweep_id}")
    os.makedirs(sweep_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  SWEEP: {len(args.policies)} policies")
    print(f"  Backend: {args.backend}")
    print(f"  Sweep dir: {sweep_dir}")
    if args.max_tasks:
        print(f"  [PILOT] max-tasks: {args.max_tasks}")
    print(f"{'='*60}\n")

    all_summaries = {}

    for policy_name in args.policies:
        print(f"\n{'─'*55}")
        print(f"  Policy: {policy_name}")
        print(f"{'─'*55}")

        sub_args = argparse.Namespace(
            dataset=None,
            backend=args.backend,
            policy=policy_name,
            config=args.config,
            tasks=args.tasks,
            difficulty=args.difficulty,
        )
        sub_config = dict(config)
        sub_config["policy"] = {**config.get("policy", {}), "name": policy_name}

        if args.max_tasks:
            from tasks import load_tasks
            limited = [t.instance_id for t in load_tasks()[:args.max_tasks]]
            sub_args.tasks = args.tasks or limited

        try:
            summary = run_benchmark(sub_args, sub_config)
            all_summaries[policy_name] = summary
        except Exception as e:
            print(f"[ERROR] Policy {policy_name} failed: {e}")
            all_summaries[policy_name] = {"error": str(e)}

    print(f"\n{'='*60}")
    print("  Comparison table of policies")
    print(f"{'='*60}")

    _print_comparison_table(all_summaries, backend=args.backend)

    comparison_path = os.path.join(sweep_dir, "comparison.json")
    with open(comparison_path, "w", encoding="utf-8") as f:
        json.dump({
            "sweep_id": sweep_id,
            "git_commit": _git_commit(),
            "backend": args.backend,
            "timestamp": datetime.now().isoformat(),
            "policies": args.policies,
            "summaries": all_summaries,
        }, f, indent=2, ensure_ascii=False)

    _write_comparison_md(all_summaries, sweep_dir, args.backend, sweep_id)


def _print_comparison_table(summaries: dict, backend: str = ""):
    cur = "₽" if backend == "polza" else "$"
    hdr_cost = f"AvgCost{cur}"
    header = f"{'Policy':<25} {'Solved%':>8} {hdr_cost:>10} {'Utility':>9} {'StrongEsc%':>11} {'HumanEsc%':>10}"
    print(header)
    print("─" * len(header))

    for policy, s in summaries.items():
        if "error" in s:
            print(f"  {policy:<23} ERROR: {s['error'][:40]}")
            continue
        solved_pct  = s.get("solved_rate", 0) * 100
        avg_cost    = s.get("avg_cost_usd", 0.0)
        utility     = s.get("utility", 0.0)
        strong_pct  = s.get("escalation_to_strong_rate", 0) * 100
        human_pct   = s.get("escalation_to_human_rate", 0) * 100
        print(f"  {policy:<23} {solved_pct:>7.1f}% {avg_cost:>9.4f}{cur} {utility:>9.4f} "
              f"{strong_pct:>10.1f}% {human_pct:>9.1f}%")


def _write_comparison_md(summaries: dict, sweep_dir: str, backend: str, sweep_id: str):
    lines = [
        "# Comparison of policy escalation\n",
        f"**Sweep:** `{sweep_id}`  ",
        f"**Backend:** `{backend}`  ",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  ",
        f"**Git:** `{_git_commit()}`\n",
        "## Main table\n",
        "| Policy | Solve rate | Avg cost (USD) | Median cost | Avg iter | Strong esc % | Human esc % | Utility |",
        "|--------|-----------|----------------|-------------|----------|-------------|------------|---------|",
    ]

    for policy, s in summaries.items():
        if "error" in s:
            lines.append(f"| {policy} | ERROR | — | — | — | — | — | — |")
            continue
        cur = "₽" if backend == "polza" else "$"
        lines.append(
            f"| {policy} "
            f"| {s.get('solved_rate',0):.1%} "
            f"| {cur}{s.get('avg_cost_usd',0.0):.4f} "
            f"| {cur}{s.get('median_cost_usd', s.get('avg_cost_usd',0.0)):.4f} "
            f"| {s.get('avg_iterations',0.0):.2f} "
            f"| {s.get('escalation_to_strong_rate',0):.1%} "
            f"| {s.get('escalation_to_human_rate',0):.1%} "
            f"| {s.get('utility',0.0):.4f} |"
        )


    with open(os.path.join(sweep_dir, "comparison.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()