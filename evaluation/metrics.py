"""
Автоматический расчёт метрик по результатам прогона.
Вход: список metrics-объектов из runs/run_XXX/metrics.json
"""
from typing import List, Dict, Any


def compute_summary(metrics: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Возвращает агрегированные метрики по всем задачам."""
    n = len(metrics)
    if n == 0:
        return {}

    solved = [m for m in metrics if m.get("solved")]
    escalated_strong = [m for m in metrics if m.get("escalated_to_strong")]
    escalated_human  = [m for m in metrics if m.get("escalated_to_human")]

    def avg(values):
        return round(sum(values) / len(values), 3) if values else 0.0

    return {
        # основные
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

        # итерации
        "avg_iterations":          avg([m.get("total_iterations", 0) for m in metrics]),
        "avg_iterations_solved":   avg([m.get("total_iterations", 0) for m in solved]),

        # эскалации
        "escalation_to_strong_rate": round(len(escalated_strong) / n, 3),
        "escalation_to_human_rate":  round(len(escalated_human)  / n, 3),

        # по сложности
        "by_difficulty": _breakdown_by_difficulty(metrics),
    }


def _breakdown_by_difficulty(metrics: List[Dict]) -> Dict[str, Any]:
    """Разбивка solved_rate и avg_cost по easy/medium/hard."""
    groups: Dict[str, List] = {"easy": [], "medium": [], "hard": []}
    for m in metrics:
        d = m.get("difficulty", "unknown")
        if d in groups:
            groups[d].append(m)

    result = {}
    for diff, group in groups.items():
        if not group:
            continue
        solved = sum(1 for m in group if m.get("solved"))
        result[diff] = {
            "count":       len(group),
            "solved":      solved,
            "solved_rate": round(solved / len(group), 3),
            "avg_cost":    round(sum(m.get("cost_score", 0) for m in group) / len(group), 2),
            "avg_iters":   round(sum(m.get("total_iterations", 0) for m in group) / len(group), 1),
        }
    return result


def compute_regret(policy_metrics: List[Dict], oracle_metrics: List[Dict]) -> Dict[str, float]:
    """
    Policy regret = J(oracle) - J(policy).
    oracle_metrics - результаты Oracle policy (верхняя граница).
    """
    def avg_cost(ms):
        return sum(m.get("cost_score", 0) for m in ms) / max(len(ms), 1)

    def solved_rate(ms):
        return sum(1 for m in ms if m.get("solved")) / max(len(ms), 1)

    oracle_solved = solved_rate(oracle_metrics)
    policy_solved = solved_rate(policy_metrics)
    oracle_cost   = avg_cost(oracle_metrics)
    policy_cost   = avg_cost(policy_metrics)

    return {
        "solved_rate_regret": round(oracle_solved - policy_solved, 3),
        "cost_regret":        round(policy_cost   - oracle_cost,   3),
    }


def print_summary(summary: Dict[str, Any], policy_name: str = ""):
    title = f"Metrics: {policy_name}" if policy_name else "Metrics"
    print(f"\n{'-'*50}")
    print(f"  {title}")
    print(f"{'-'*50}")
    print(f"  Solved         : {summary['solved_count']}/{summary['total_tasks']}"
          f" ({summary['solved_rate']*100:.0f}%)")
    print(f"  Avg pass rate  : {summary['avg_final_pass_rate']:.3f}")
    print(f"  Avg cost       : {summary['avg_cost']:.1f}")
    print(f"  Avg iterations : {summary['avg_iterations']:.1f}")
    print(f"  Escal to strong: {summary['escalation_to_strong_rate']*100:.0f}%")
    print(f"  Escal to human : {summary['escalation_to_human_rate']*100:.0f}%")
    print(f"\n  By difficulty:")
    for diff, bd in summary.get("by_difficulty", {}).items():
        print(f"    {diff:8s} : {bd['solved']}/{bd['count']} solved"
              f"  cost={bd['avg_cost']:.1f}  iters={bd['avg_iters']:.1f}")
    print(f"{'-'*50}\n")