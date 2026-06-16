"""
mas_runner.py — запуск мультиагентного бенчмарка.
"""

import sys, os, json
sys.path.insert(0, os.path.dirname(__file__))

from tasks import make_tasks
from environments.environment import Environment
from agents.base import AgentRole, ModelTier, Message
from agents.developer import DeveloperAgent
from agents.reviewer import ReviewerAgent
from agents.tester import TesterAgent
from agents.manager import ManagerAgent, ManagerPolicy, MANAGER_DECISIONS


def run_task(task, verbose=True) -> list[dict]:
    """
    Запускает мультиагентный пайплайн для одной задачи.
    Возвращает трассировку — список событий.
    """
    trace  = []
    env    = Environment(task)
    policy = ManagerPolicy(
        max_weak_attempts=2,
        max_strong_attempts=1,
        confidence_threshold=0.3,
        max_total_iterations=7,
    )

    manager    = ManagerAgent(policy)
    reviewer   = ReviewerAgent()
    tester     = TesterAgent(env)
    weak_dev   = DeveloperAgent(tier=ModelTier.WEAK)
    strong_dev = DeveloperAgent(tier=ModelTier.STRONG)

    def log(event_type: str, sender: str, recipient: str, details: dict):
        entry = {"event": event_type, "from": sender, "to": recipient, **details}
        trace.append(entry)
        if verbose:
            _print_event(entry)

    if verbose:
        print(f"\n  Старт задачи {task.task_id} | сложность: {task.difficulty}")
        print(f" {task.issue_text[:80]}...")

    hint_for_dev   = ""
    final_decision = None

    for _iteration in range(policy.max_total_iterations):

        current_dev = weak_dev if manager.current_tier == ModelTier.WEAK else strong_dev
        tier_label  = manager.current_tier.value

        # Developer генерирует код + оценивает уверенность
        dev_msg = current_dev.generate(
            task_id       = task.task_id,
            issue_text    = task.issue_text,
            original_code = task.original_code,
            reviewer_hint = hint_for_dev,
        )
        manager.register_attempt(manager.current_tier)

        log("generate_code", AgentRole.DEVELOPER.value, AgentRole.MANAGER.value, {
            "tier":          tier_label,
            "attempt":       dev_msg.content["attempt"],
            "confidence":    dev_msg.content["confidence"],
            "cant_solve":    dev_msg.content["cant_solve"],
            "hint_received": bool(hint_for_dev),
            "code_lines":    len(dev_msg.content["code"].splitlines()),
        })

        # Manager смотрит на confidence
        # Если confidence низкий — пропускаем Reviewer и Tester
        decision, reason = manager.decide_after_generate(dev_msg)
        log("manager_decision", AgentRole.MANAGER.value, "→", {
            "decision": decision,
            "label":    MANAGER_DECISIONS.get(decision, decision),
            "reason":   reason,
            "phase":    "after_generate",
        })

        # Если Manager решил не идти к Reviewer — обрабатываем сразу
        if decision != "send_to_review":
            decision, final_decision, hint_for_dev = _handle_decision(
                decision, dev_msg, None, hint_for_dev, log
            )
            if final_decision:
                break
            continue

        # Reviewer проверяет код
        # Добавляем контекст задачи в сообщение для Reviewer
        dev_msg.content["original_code"] = task.original_code
        dev_msg.content["issue_text"]    = task.issue_text

        review_msg = reviewer.review(dev_msg)
        log("code_review", AgentRole.REVIEWER.value, AgentRole.MANAGER.value, {
            "quality_score":  review_msg.content["quality_score"],
            "issues":         review_msg.content["issues_found"],
            "recommendation": review_msg.content["recommendation"],
            "hint":           review_msg.content["hint_for_developer"],
        })

        # Manager смотрит на заключение ревьюера
        decision, reason = manager.decide_after_review(review_msg)
        log("manager_decision", AgentRole.MANAGER.value, "→", {
            "decision": decision,
            "label":    MANAGER_DECISIONS.get(decision, decision),
            "reason":   reason,
            "phase":    "after_review",
        })

        if decision != "send_to_test":
            decision, final_decision, hint_for_dev = _handle_decision(
                decision, dev_msg, review_msg, hint_for_dev, log
            )
            if final_decision:
                break
            continue

        # Tester
        test_msg = tester.test(
            code       = dev_msg.content["code"],
            model_name = current_dev.model_name,
        )
        log("run_tests", AgentRole.TESTER.value, AgentRole.MANAGER.value, {
            "pass_rate":    test_msg.content["pass_rate"],
            "tests_passed": test_msg.content["tests_passed"],
            "tests_total":  test_msg.content["tests_total"],
            "failures":     test_msg.content["failure_reasons"],
        })

        # Manager смотрит на результат тестов
        decision, reason = manager.decide_after_test(test_msg)
        log("manager_decision", AgentRole.MANAGER.value, "→", {
            "decision": decision,
            "label":    MANAGER_DECISIONS.get(decision, decision),
            "reason":   reason,
            "phase":    "after_test",
        })

        _, final_decision, hint_for_dev = _handle_decision(
            decision, dev_msg, review_msg, hint_for_dev, log
        )
        if final_decision:
            break

    else:
        final_decision = "max_iterations_reached"

    if verbose:
        print(f"\n  Итог: {final_decision}")

    trace.append({"event": "final", "outcome": final_decision})
    return trace


def _handle_decision(
    decision: str,
    dev_msg: Message,
    review_msg: Message | None,
    hint_for_dev: str,
    log,
) -> tuple[str, str | None, str]:
    """
    Обрабатывает финальные решения Manager.
    Возвращает (decision, final_decision_or_None, новый_hint).

    final_decision != None означает что пайплайн нужно завершить.
    """
    if decision == "accept":
        return decision, "success", hint_for_dev

    if decision == "stop":
        return decision, "stopped", hint_for_dev

    if decision == "escalate_human":
        log("escalation_event", AgentRole.MANAGER.value, AgentRole.HUMAN.value, {
            "message": "Задача передана человеку",
        })
        return decision, "human_escalated", hint_for_dev

    if decision == "escalate_strong":
        # При эскалации на strong - сбрасываем подсказки ревьюера
        return decision, None, ""

    if decision == "request_changes":
        # Подсказку берём от ревьюера если он был, иначе пустая строка
        new_hint = ""
        if review_msg is not None:
            new_hint = review_msg.content.get("hint_for_developer", "")
        return decision, None, new_hint

    return decision, None, hint_for_dev


def _print_event(e: dict):
    """Красивый вывод события в терминал."""
    evt = e["event"]
    frm = e.get("from", "")
    to  = e.get("to", "")

    if evt == "generate_code":
        tier = e["tier"].upper()
        att  = e["attempt"]
        conf = e.get("confidence", 1.0)
        conf_bar = "█" * int(conf * 10) + "░" * (10 - int(conf * 10))
        cant = " cant_solve" if e.get("cant_solve") else ""
        hint = " + подсказка ревьюера" if e["hint_received"] else ""
        print(f"\n  [{frm} → {to}] Developer ({tier}, попытка {att}){hint}{cant}")
        print(f"                  confidence: {conf:.2f} [{conf_bar}] | {e['code_lines']} строк")

    elif evt == "code_review":
        q   = e["quality_score"]
        iss = ", ".join(e["issues"]) if e["issues"] else "—"
        rec = e["recommendation"]
        bar = "█" * int(q * 10) + "░" * (10 - int(q * 10))
        print(f"  [{frm} → {to}] Ревью: {q:.2f} [{bar}] | {iss} | вердикт: {rec}")
        if rec != "approve":
            print(f" {e.get('hint', '')[:80]}")

    elif evt == "run_tests":
        pr  = e["pass_rate"]
        bar = "█" * int(pr * 10) + "░" * (10 - int(pr * 10))
        fail = "; ".join(e["failures"][:2]) if e["failures"] else "—"
        print(f"  [{frm} → {to}] Тесты: {e['tests_passed']}/{e['tests_total']} [{bar}] | {fail}")

    elif evt == "manager_decision":
        phase = e.get("phase", "")
        print(f"  [Manager] [{phase}] {e['label']}")
        print(f" {e['reason'][:70]}")

    elif evt == "escalation_event":
        print(f"\n [{frm} → {to}] {e['message']}")


def compute_mas_metrics(task, trace: list[dict]) -> dict:
    """Агрегированные метрики по трассировке задачи."""
    outcome    = next((e["outcome"] for e in trace if e["event"] == "final"), "unknown")
    decisions  = [e for e in trace if e["event"] == "manager_decision"]
    esc_strong = [d for d in decisions if d["decision"] == "escalate_strong"]
    esc_human  = [d for d in decisions if d["decision"] == "escalate_human"]
    reviews    = [e for e in trace if e["event"] == "code_review"]
    tests      = [e for e in trace if e["event"] == "run_tests"]
    generates  = [e for e in trace if e["event"] == "generate_code"]

    final_pass_rate = tests[-1]["pass_rate"] if tests else 0.0
    avg_quality     = (sum(r["quality_score"] for r in reviews) / len(reviews)) if reviews else 0.0
    avg_confidence  = (sum(g["confidence"] for g in generates) / len(generates)) if generates else 0.0
    cant_solve_cnt  = sum(1 for g in generates if g.get("cant_solve"))

    # Стоимость: weak=1, strong=3, human=10 за итерацию
    cost = 0.0
    for e in trace:
        if e["event"] == "generate_code":
            cost += 1.0 if e["tier"] == "weak" else 3.0
        if e.get("decision") == "escalate_human":
            cost += 10.0

    return {
        "task_id":             task.task_id,
        "difficulty":          task.difficulty,
        "outcome":             outcome,
        "solved":              outcome == "success",
        "total_iterations":    len(generates),
        "escalated_to_strong": len(esc_strong) > 0,
        "escalated_to_human":  len(esc_human) > 0,
        "final_pass_rate":     round(final_pass_rate, 2),
        "avg_review_quality":  round(avg_quality, 2),
        "avg_confidence":      round(avg_confidence, 2),
        "cant_solve_count":    cant_solve_cnt,
        "cost_score":          round(cost, 1),
        "num_reviews":         len(reviews),
        "num_test_runs":       len(tests),
    }


def print_sep(char="─", w=65):
    print(char * w)


if __name__ == "__main__":
    tasks       = make_tasks()
    all_metrics = []
    all_traces  = []

    for task in tasks:
        print_sep("═")
        trace = run_task(task, verbose=True)
        m     = compute_mas_metrics(task, trace)
        all_metrics.append(m)
        all_traces.append({
            "task_id":    task.task_id,
            "difficulty": task.difficulty,
            "metrics":    m,
            "trace":      trace,
        })

    print("\n")
    print_sep("═")
    print(" ИТОГОВЫЕ МЕТРИКИ")
    print_sep("═")
    print(f"  {'Задача':<8} {'Сложность':<10} {'Итог':<22} "
          f"{'Итер.':<7} {'Цена':<8} {'Pass%':<8} {'Conf':<8} {'Эскалация'}")
    print_sep()
    for m in all_metrics:
        esc = "→ strong" if m["escalated_to_strong"] else ("→ human" if m["escalated_to_human"] else "—")
        print(f"  {m['task_id']:<8} {m['difficulty']:<10} { m['outcome']:<22} "
              f"{m['total_iterations']:<7} {m['cost_score']:<8} "
              f"{m['final_pass_rate']:<8.0%} {m['avg_confidence']:<8.2f} {esc}")

    print_sep()
    solved    = sum(1 for m in all_metrics if m["solved"])
    avg_cost  = sum(m["cost_score"] for m in all_metrics) / len(all_metrics)
    avg_conf  = sum(m["avg_confidence"] for m in all_metrics) / len(all_metrics)
    print(f"  Решено: {solved}/{len(all_metrics)} | "
          f"Ср. стоимость: {avg_cost:.1f} | "
          f"Ср. уверенность: {avg_conf:.2f}")
    print_sep("═")

    traces_path = os.path.join(os.path.dirname(__file__), "docs/mas_traces.json")
    with open(traces_path, "w", encoding="utf-8") as f:
        json.dump({"tasks": all_traces}, f, ensure_ascii=False, indent=2)
    print(f" Трассировки сохранены в mas_traces.json")
    print_sep("═")