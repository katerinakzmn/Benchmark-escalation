import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from tasks import make_tasks
from environment import Environment
from agents.base import AgentRole, ModelTier, Message
from agents.developer import DeveloperAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from agents.manager import ManagerAgent, ManagerPolicy, MANAGER_DECISIONS


def run_task(task, verbose=True) -> list[dict]:
    trace = []
    env = Environment(task)
    policy = ManagerPolicy(max_weak_attempts=2, max_strong_attempts=1, max_total_iterations=7)

    # Создаём команду агентов
    manager  = ManagerAgent(policy)
    reviewer = ReviewerAgent()
    tester   = TesterAgent(env)
    weak_dev  = DeveloperAgent(tier=ModelTier.WEAK)
    strong_dev = DeveloperAgent(tier=ModelTier.STRONG)

    def log(event_type: str, sender: str, recipient: str, details: dict):
        entry = {"event": event_type, "from": sender, "to": recipient, **details}
        trace.append(entry)
        if verbose:
            _print_event(entry)

    # менеджер назначает задачу
    if verbose:
        print(f"\n  Старт задачи {task.task_id} | сложность: {task.difficulty}")
        print(f"  {task.description[:80]}...")

    hint_for_dev = ""
    final_decision = None

    # Главный цикл
    for iteration in range(policy.max_total_iterations):

        # Определяем текущего разработчика
        current_dev = weak_dev if manager.current_tier == ModelTier.WEAK else strong_dev
        tier_label = manager.current_tier.value

        # Developer пишет код
        dev_msg = current_dev.generate(task.task_id, reviewer_hint=hint_for_dev)
        manager.register_attempt(manager.current_tier)
        log("generate_code", AgentRole.DEVELOPER.value, AgentRole.REVIEWER.value, {
            "tier": tier_label,
            "attempt": dev_msg.content["attempt"],
            "hint_received": bool(hint_for_dev),
            "code_lines": len(dev_msg.content["code"].splitlines()),
        })

        # Reviewer проверяет код
        review_msg = reviewer.review(dev_msg)
        log("code_review", AgentRole.REVIEWER.value, AgentRole.MANAGER.value, {
            "quality_score": review_msg.content["quality_score"],
            "issues": review_msg.content["issues_found"],
            "recommendation": review_msg.content["recommendation"],
        })

        # Manager решает после ревью
        decision, reason = manager.decide_after_review(review_msg)
        log("manager_decision", AgentRole.MANAGER.value, "→", {
            "decision": decision,
            "label": MANAGER_DECISIONS.get(decision, decision),
            "reason": reason,
        })

        if decision == "send_to_test":
            # Tester запускает тесты
            test_msg = tester.test(
                code=dev_msg.content["code"],
                model_name=current_dev.model_name,
            )
            log("run_tests", AgentRole.TESTER.value, AgentRole.MANAGER.value, {
                "pass_rate": test_msg.content["pass_rate"],
                "tests_passed": test_msg.content["tests_passed"],
                "tests_total": test_msg.content["tests_total"],
                "failures": test_msg.content["failure_reasons"],
            })

            # Manager решает после тестов
            decision, reason = manager.decide_after_test(test_msg)
            log("manager_decision", AgentRole.MANAGER.value, "→", {
                "decision": decision,
                "label": MANAGER_DECISIONS.get(decision, decision),
                "reason": reason,
            })
        if decision == "request_changes_weak":
            hint_for_dev = review_msg.content.get("hint_for_developer", "")
        # Обработка решения менеджера
        if decision == "accept":
            final_decision = "success"
            break

        elif decision == "stop":
            final_decision = "stopped"
            break

        elif decision == "escalate_human":
            log("escalation_event", AgentRole.MANAGER.value, AgentRole.HUMAN.value, {
                "message": "Задача передана человеку-разработчику",
            })
            final_decision = "human_escalated"
            break

        elif decision == "escalate_strong":
            # Следующая итерация будет с сильным разработчиком
            hint_for_dev = ""  # сильному не нужны подсказки от ревьюера

        elif decision in ("request_changes_weak",):
            # Передаём подсказку разработчику для следующей итерации
            hint_for_dev = review_msg.content.get("hint_for_developer", "")

    else:
        final_decision = "max_iterations_reached"

    if verbose:
        print(f"\n   Итог: {final_decision}")

    trace.append({"event": "final", "outcome": final_decision})
    return trace


def _print_event(e: dict):
    """Красивый вывод одного события трассировки."""
    evt = e["event"]
    frm = e.get("from", "")
    to  = e.get("to", "")

    if evt == "generate_code":
        tier = e["tier"].upper()
        att  = e["attempt"]
        hint = " + подсказка ревьюера" if e["hint_received"] else ""
        print(f"\n  [{frm} → {to}] Разработчик ({tier}, попытка {att}){hint} написал код ({e['code_lines']} строк)")

    elif evt == "code_review":
        q    = e["quality_score"]
        iss  = ", ".join(e["issues"]) if e["issues"] else "—"
        rec  = e["recommendation"]
        bar  = "█" * int(q * 10) + "░" * (10 - int(q * 10))
        print(f"  [{frm} → {to}] Ревью: качество {q:.2f} [{bar}] | проблемы: {iss} | вердикт: {rec}")

    elif evt == "run_tests":
        pr   = e["pass_rate"]
        bar  = "█" * int(pr * 10) + "░" * (10 - int(pr * 10))
        fail = "; ".join(e["failures"][:2]) if e["failures"] else "—"
        print(f"  [{frm} → {to}] Тесты: {e['tests_passed']}/{e['tests_total']} [{bar}] | {fail}")

    elif evt == "manager_decision":
        lbl = e["label"]
        rsn = e["reason"][:70]
        print(f"  [{frm}] Решение: {lbl}")
        print(f"          ↳ {rsn}")

    elif evt == "escalation_event":
        print(f"\n    [{frm} → {to}] {e['message']}")


def compute_mas_metrics(task, trace: list[dict]) -> dict:
    """Считает метрики по мультиагентной трассировке."""
    outcome = next((e["outcome"] for e in trace if e["event"] == "final"), "unknown")
    decisions = [e for e in trace if e["event"] == "manager_decision"]
    escalations_strong = [d for d in decisions if d["decision"] == "escalate_strong"]
    escalations_human  = [d for d in decisions if d["decision"] == "escalate_human"]
    review_events = [e for e in trace if e["event"] == "code_review"]
    test_events   = [e for e in trace if e["event"] == "run_tests"]

    final_pass_rate = test_events[-1]["pass_rate"] if test_events else 0.0
    avg_quality = (sum(r["quality_score"] for r in review_events) / len(review_events)) if review_events else 0.0

    # Стоимость: weak=1, strong=3, human=10 за итерацию
    cost = 0.0
    for e in trace:
        if e["event"] == "generate_code":
            cost += 1.0 if e["tier"] == "weak" else 3.0
        if e.get("decision") == "escalate_human":
            cost += 10.0

    return {
        "task_id":              task.task_id,
        "difficulty":           task.difficulty,
        "outcome":              outcome,
        "solved":               outcome == "success",
        "total_iterations":     len([e for e in trace if e["event"] == "generate_code"]),
        "escalated_to_strong":  len(escalations_strong) > 0,
        "escalated_to_human":   len(escalations_human) > 0,
        "escalation_step":      escalations_strong[0].get("step") if escalations_strong else None,
        "oracle_escalation":    task.oracle_escalation_step,
        "final_pass_rate":      round(final_pass_rate, 2),
        "avg_review_quality":   round(avg_quality, 2),
        "cost_score":           round(cost, 1),
        "num_reviews":          len(review_events),
        "num_test_runs":        len(test_events),
    }


def print_separator(char="─", w=65):
    print(char * w)


if __name__ == "__main__":
    tasks = make_tasks()
    all_metrics = []

    for task in tasks:
        print_separator("═")
        trace = run_task(task, verbose=True)
        m = compute_mas_metrics(task, trace)
        all_metrics.append(m)

    # ── Итоговая таблица ─────────────────────────────────────────────────────
    print("\n")
    print_separator("═")
    print("  ИТОГОВЫЕ МЕТРИКИ")
    print_separator("═")
    print(f"  {'Задача':<8} {'Сложность':<10} {'Итог':<22} {'Итераций':<10} "
          f"{'Стоимость':<12} {'Pass rate':<12} {'Эскалация'}")
    print_separator()
    for m in all_metrics:
        esc = "→ strong" if m["escalated_to_strong"] else ("→ human" if m["escalated_to_human"] else "—")
        outcome_icon = {"success": "success", "human_escalated": "human", "stopped": "stop"}.get(m["outcome"], m["outcome"])
        print(f"  {m['task_id']:<8} {m['difficulty']:<10} {outcome_icon:<22} {m['total_iterations']:<10} "
              f"{m['cost_score']:<12} {m['final_pass_rate']:<12.0%} {esc}")

    print_separator()
    solved = sum(1 for m in all_metrics if m["solved"])
    avg_cost = sum(m["cost_score"] for m in all_metrics) / len(all_metrics)
    avg_iters = sum(m["total_iterations"] for m in all_metrics) / len(all_metrics)
    print(f"  Решено: {solved}/{len(all_metrics)} | Средняя стоимость: {avg_cost:.1f} | Средних итераций: {avg_iters:.1f}")
    print_separator("═")

    # Сохраняем трассировки
    with open(os.path.join(os.path.dirname(__file__), "mas_traces.json"), "w", encoding="utf-8") as f:
        json.dump({"tasks": [compute_mas_metrics(t, []) for t in tasks]}, f, ensure_ascii=False, indent=2)
    print("  Трассировки сохранены в mas_traces.json")
    print_separator("═")