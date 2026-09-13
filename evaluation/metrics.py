from collections import defaultdict
from typing import List, Dict, Any

def compute_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(metrics)
    if n == 0:
        return {
            "total_tasks": 0, "solved_count": 0, "solved_rate": 0.0,
            "avg_final_pass_rate": 0.0, "avg_pass_rate_solved": 0.0,
            "avg_cost": 0.0, "avg_cost_solved": 0.0, "total_cost": 0.0,
            "avg_cost_usd": 0.0, "total_cost_usd": 0.0,
            "utility": 0.0,
            "avg_iterations": 0.0, "avg_iterations_solved": 0.0,
            "escalation_to_strong_rate": 0.0, "escalation_to_human_rate": 0.0,
            "status_counts": {},
            "by_difficulty": {},
            "by_domain":     {},
            "by_defect_type":{},
        }

    solved = [m for m in metrics if m.get("solved")]
    escalated_strong = [m for m in metrics if m.get("escalated_to_strong")]
    escalated_human  = [m for m in metrics if m.get("escalated_to_human")]

    def avg(values):
        return round(sum(values) / len(values), 6) if values else 0.0

    cost_usd_values = [m.get("cost_usd", None) for m in metrics]
    has_real_cost = any(v is not None for v in cost_usd_values)

    if has_real_cost:
        avg_cost_usd   = avg([v if v is not None else 0.0 for v in cost_usd_values])
        total_cost_usd = round(sum(v if v is not None else 0.0 for v in cost_usd_values), 9)
    else:
        avg_cost_usd   = 0.0
        total_cost_usd = 0.0

    # Utility: r = -λ * cost_usd + W * solved  (λ=0.01, W=1.0)
    _LAMBDA = 0.01
    _W      = 1.0

    def _task_utility(m: Dict[str, Any]) -> float:
        c = m.get("cost_usd", 0.0) or 0.0
        s = 1.0 if m.get("solved") else 0.0
        return -_LAMBDA * c + _W * s

    utility = avg([_task_utility(m) for m in metrics])

    # Status breakdown
    status_counts: Dict[str, int] = defaultdict(int)
    for m in metrics:
        status = m.get("status", "unknown")
        status_counts[status] += 1
    status_counts = dict(status_counts)

    return {
        # main
        "total_tasks":             n,
        "solved_count":            len(solved),
        "solved_rate":             round(len(solved) / n, 3),

        # pass rate
        "avg_final_pass_rate":     avg([m.get("final_pass_rate", 0) for m in metrics]),
        "avg_pass_rate_solved":    avg([m.get("final_pass_rate", 0) for m in solved]),

        # стоимость
        "avg_cost":                avg([m.get("cost_score", 0) for m in metrics]),
        "avg_cost_solved":         avg([m.get("cost_score", 0) for m in solved]),
        "total_cost":              round(sum(m.get("cost_score", 0) for m in metrics), 2),

        # реальная стоимость в валюте провайдера
        "avg_cost_usd":            avg_cost_usd,
        "total_cost_usd":          total_cost_usd,
        "currency_symbol":         "₽",

        # utility
        "utility":                 round(utility, 6),

        # итерации
        "avg_iterations":          avg([m.get("total_iterations", 0) for m in metrics]),
        "avg_iterations_solved":   avg([m.get("total_iterations", 0) for m in solved]),

        # эскалации
        "escalation_to_strong_rate": round(len(escalated_strong) / n, 3),
        "escalation_to_human_rate":  round(len(escalated_human)  / n, 3),

        # статусы
        "status_counts":           status_counts,

        # по сложности
        "by_difficulty": _breakdown_by_difficulty(metrics),

        # по домену и типу дефекта
        "by_domain":      _breakdown_by_field(metrics, "domain"),
        "by_defect_type": _breakdown_by_field(metrics, "defect_type"),
    }


def compute_regret(
    policy_metrics: List[Dict[str, Any]],
    oracle_metrics: List[Dict[str, Any]],
) -> float:
    _LAMBDA = 0.01
    _W      = 1.0

    def _utility(m: Dict[str, Any]) -> float:
        # Prefer real cost_usd; fall back to cost_score * 0.01 (normalised proxy)
        if "cost_usd" in m and m["cost_usd"] is not None:
            cost = float(m["cost_usd"])
        else:
            cost = float(m.get("cost_score", 0)) * 0.01
        s = 1.0 if m.get("solved") else 0.0
        return -_LAMBDA * cost + _W * s

    def _mean_utility(ms: List[Dict[str, Any]]) -> float:
        if not ms:
            return 0.0
        return sum(_utility(m) for m in ms) / len(ms)

    return round(_mean_utility(oracle_metrics) - _mean_utility(policy_metrics), 6)



def _breakdown_by_difficulty(metrics: List[Dict]) -> Dict[str, Any]:
    groups: Dict[str, List] = defaultdict(list)
    for m in metrics:
        d = m.get("difficulty", "unknown")
        groups[d].append(m)

    result = {}
    for diff, group in groups.items():
        if not group:
            continue
        solved = sum(1 for m in group if m.get("solved"))

        # Real USD cost if available
        cost_usd_values = [m.get("cost_usd") for m in group]
        has_real_cost = any(v is not None for v in cost_usd_values)
        if has_real_cost:
            avg_cost_usd = round(
                sum(v if v is not None else 0.0 for v in cost_usd_values) / len(group), 9
            )
        else:
            avg_cost_usd = None

        result[diff] = {
            "count":        len(group),
            "solved":       solved,
            "solved_rate":  round(solved / len(group), 3),
            "avg_cost":     round(sum(m.get("cost_score", 0) for m in group) / len(group), 2),
            "avg_cost_usd": avg_cost_usd,
            "avg_iters":    round(sum(m.get("total_iterations", 0) for m in group) / len(group), 1),
        }
    return result


def _breakdown_by_field(metrics: List[Dict], field: str) -> Dict[str, Any]:
    """Breakdown by any taxonomy field (domain, defect_type, etc.)."""
    groups: Dict[str, List] = defaultdict(list)
    for m in metrics:
        val = m.get(field, "") or "unknown"
        groups[val].append(m)

    result = {}
    for key, group in sorted(groups.items()):
        if not group:
            continue
        solved = sum(1 for m in group if m.get("solved"))
        result[key] = {
            "count":       len(group),
            "solved":      solved,
            "solved_rate": round(solved / len(group), 3),
            "avg_iters":   round(sum(m.get("total_iterations", 0) for m in group) / len(group), 1),
        }
    return result



def print_summary(summary: Dict[str, Any], policy_name: str = ""):
    title = f"Metrics: {policy_name}" if policy_name else "Metrics"
    print(f"\n{'-'*50}")
    print(f"  {title}")
    print(f"{'-'*50}")
    print(f"  Solved         : {summary['solved_count']}/{summary['total_tasks']}"
          f" ({summary['solved_rate']*100:.0f}%)")
    print(f"  Avg pass rate  : {summary['avg_final_pass_rate']:.3f}")
    print(f"  Avg cost       : {summary['avg_cost']:.1f}")
    if summary.get("total_cost_usd"):
        currency_sym = summary.get("currency_symbol", "₽")
        print(f"  Total cost     : {currency_sym}{summary['total_cost_usd']:.4f}")
        print(f"  Avg cost       : {currency_sym}{summary['avg_cost_usd']:.4f}")
    print(f"  Utility        : {summary.get('utility', 0.0):.4f}")
    print(f"  Avg iterations : {summary['avg_iterations']:.1f}")
    print(f"  Escal to strong: {summary['escalation_to_strong_rate']*100:.0f}%")
    print(f"  Escal to human : {summary['escalation_to_human_rate']*100:.0f}%")
    if summary.get("status_counts"):
        print(f"\n  Status breakdown:")
        for status, count in sorted(summary["status_counts"].items()):
            print(f"    {status:15s}: {count}")
    print(f"\n  By difficulty:")
    for diff, bd in summary.get("by_difficulty", {}).items():
        currency_sym = summary.get("currency_symbol", "₽")
        cost_usd_str = (
            f"  cost={currency_sym}{bd['avg_cost_usd']:.4f}" if bd.get("avg_cost_usd") is not None else ""
        )
        print(f"    {diff:8s} : {bd['solved']}/{bd['count']} solved"
              f"  cost={bd['avg_cost']:.1f}{cost_usd_str}  iters={bd['avg_iters']:.1f}")
    # By domain
    if summary.get("by_domain"):
        print(f"\n  By domain:")
        for dom, bd in summary["by_domain"].items():
            bar = "█" * int(bd["solved_rate"] * 10) + "░" * (10 - int(bd["solved_rate"] * 10))
            print(f"    {dom:20s} {bar} {bd['solved']:>3}/{bd['count']:<3} "
                  f"({bd['solved_rate']*100:>5.1f}%)  iters={bd['avg_iters']:.1f}")

    # By defect type
    if summary.get("by_defect_type"):
        print(f"\n  By defect type:")
        for dt, bd in summary["by_defect_type"].items():
            bar = "█" * int(bd["solved_rate"] * 10) + "░" * (10 - int(bd["solved_rate"] * 10))
            print(f"    {dt:20s} {bar} {bd['solved']:>3}/{bd['count']:<3} "
                  f"({bd['solved_rate']*100:>5.1f}%)  iters={bd['avg_iters']:.1f}")

    print(f"{'-'*50}\n")