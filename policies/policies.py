"""
Реестр политик эскалации.
Каждая политика реализует метод run_task(task, backend, budget_cfg, costs_cfg) -> dict.
"""


def get_policy(name: str, cfg: dict):
    policies = {
        "fixed_weak":            FixedWeakPolicy,
        "fixed_strong":          FixedStrongPolicy,
        "retry_then_escalate":   RetryThenEscalatePolicy,
        "progress_heuristic":    ProgressHeuristicPolicy,
        "confidence_threshold":  ConfidenceThresholdPolicy,
        "human_fallback":        HumanFallbackPolicy,
        "random":                RandomPolicy,
        "oracle":                OraclePolicy,
    }
    if name not in policies:
        raise ValueError(f"Unknown policy: {name}")
    return policies[name](cfg)


class BasePolicy:
    def __init__(self, cfg: dict):
        self.cfg = cfg

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        raise NotImplementedError

    def _base_metrics(self, task_id, difficulty):
        return {
            "task_id": task_id,
            "difficulty": difficulty,
            "solved": False,
            "total_iterations": 0,
            "escalated_to_strong": False,
            "escalated_to_human": False,
            "final_pass_rate": 0.0,
            "cost_score": 0.0,
        }

    def _run_tests(self, task, code: str) -> dict:
        from environments.environment import Environment
        env = Environment(task)
        result = env.run(code, model_used="mock", step_number=1)
        return {"pass_rate": result.pass_rate, "success": result.success}

    def _make_trace_record(self, task_id: str, steps: list, metrics: dict) -> dict:
        """
        Семантика: done = эпизод завершён, solved = задача решена.
        """
        for step in steps:
            step["episode_id"] = f"{task_id}_ep"
            step["task_id"] = task_id
        # Последний шаг — конец эпизода в любом случае
        if steps:
            steps[-1]["done"] = True
        return {
            "task_id": task_id,
            "policy": self.__class__.__name__,
            "metrics": metrics,
            "trace": steps,
        }


class FixedWeakPolicy(BasePolicy):
    """Всегда использует только weak модель."""

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        max_iter = budget_cfg.get("max_total_iterations", 7)
        steps = []
        cost = 0.0

        for i in range(1, max_iter + 1):
            code = backend.generate(task.instance_id, "weak")
            test_result = self._run_tests(task, code)
            cost += costs_cfg.get("weak_call", 1) + costs_cfg.get("test_run", 0.5)

            step = {
                "step": i,
                "state": {"tier": "weak", "iteration": i, "cost_so_far": round(cost, 2)},
                "action": "retry_weak",
                "next_state": {"pass_rate": test_result["pass_rate"]},
                "reward": 1.0 if test_result["success"] else -0.5,
                "done": test_result["success"],
            }
            steps.append(step)

            if test_result["success"]:
                metrics["solved"] = True
                metrics["final_pass_rate"] = test_result["pass_rate"]
                break

        metrics["total_iterations"] = len(steps)
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, steps, metrics)}


class FixedStrongPolicy(BasePolicy):
    """Всегда использует только strong модель."""

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        metrics["escalated_to_strong"] = True
        cost = 0.0

        code = backend.generate(task.instance_id, "strong")
        test_result = self._run_tests(task, code)
        cost += costs_cfg.get("strong_call", 3) + costs_cfg.get("test_run", 0.5)

        step = {
            "step": 1,
            "state": {"tier": "strong", "iteration": 1, "cost_so_far": round(cost, 2)},
            "action": "use_strong",
            "next_state": {"pass_rate": test_result["pass_rate"]},
            "reward": 1.0 if test_result["success"] else -0.5,
            "done": test_result["success"],
        }

        metrics["solved"] = test_result["success"]
        metrics["final_pass_rate"] = test_result["pass_rate"]
        metrics["total_iterations"] = 1
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, [step], metrics)}


class RetryThenEscalatePolicy(BasePolicy):
    """Try weak N times, then strong M times, then human fallback."""

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        max_weak   = self.cfg.get("max_weak_attempts", 2)
        max_strong = self.cfg.get("max_strong_attempts", 1)
        steps = []
        cost = 0.0
        step_n = 0

        for tier, max_attempts, cost_key in [
            ("weak",   max_weak,   "weak_call"),
            ("strong", max_strong, "strong_call"),
            ("human",  1,          "human_call"),
        ]:
            for _ in range(max_attempts):
                step_n += 1
                code = backend.generate(task.instance_id, tier)
                test_result = self._run_tests(task, code)
                cost += costs_cfg.get(cost_key, 1) + costs_cfg.get("test_run", 0.5)

                if tier == "strong":
                    metrics["escalated_to_strong"] = True
                if tier == "human":
                    metrics["escalated_to_human"] = True

                step = {
                    "step": step_n,
                    "state": {"tier": tier, "iteration": step_n, "cost_so_far": round(cost, 2)},
                    "action": f"use_{tier}",
                    "next_state": {"pass_rate": test_result["pass_rate"]},
                    "reward": 1.0 if test_result["success"] else -0.5,
                    "done": test_result["success"],
                }
                steps.append(step)

                if test_result["success"]:
                    metrics["solved"] = True
                    metrics["final_pass_rate"] = test_result["pass_rate"]
                    metrics["total_iterations"] = step_n
                    metrics["cost_score"] = round(cost, 2)
                    return {"metrics": metrics, "trace_record": self._make_trace_record(
                        task.instance_id, steps, metrics)}

        metrics["total_iterations"] = step_n
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, steps, metrics)}


class ProgressHeuristicPolicy(BasePolicy):
    """Эскалирует если pass_rate не растёт K итераций подряд."""

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        k = self.cfg.get("zero_progress_limit", 2)
        max_iter = budget_cfg.get("max_total_iterations", 7)
        tier = "weak"
        prev_pass_rate = -1.0
        stall_count = 0
        steps = []
        cost = 0.0

        for i in range(1, max_iter + 1):
            code = backend.generate(task.instance_id, tier)
            test_result = self._run_tests(task, code)
            cost_key = {"weak": "weak_call", "strong": "strong_call", "human": "human_call"}[tier]
            cost += costs_cfg.get(cost_key, 1) + costs_cfg.get("test_run", 0.5)

            progress = test_result["pass_rate"] - prev_pass_rate
            stall_count = 0 if progress > 0.01 else stall_count + 1
            prev_pass_rate = test_result["pass_rate"]

            state_tier = tier
            if test_result["success"]:
                action = "solved"
            elif stall_count >= k and tier == "weak":
                action = "escalate_to_strong"
                tier = "strong"
                metrics["escalated_to_strong"] = True
                stall_count = 0
            elif stall_count >= k and tier == "strong":
                action = "escalate_to_human"
                tier = "human"
                metrics["escalated_to_human"] = True
                stall_count = 0
            else:
                action = f"retry_{tier}"

            step = {
                "step": i,
                "state": {"tier": state_tier, "iteration": i,
                          "pass_rate_prev": round(prev_pass_rate, 3),
                          "stall_count": stall_count, "cost_so_far": round(cost, 2)},
                "action": action,
                "next_state": {"tier": tier, "pass_rate": test_result["pass_rate"]},
                "reward": 1.0 if test_result["success"] else (-0.3 if progress > 0 else -0.5),
                "done": test_result["success"],
            }
            steps.append(step)

            if test_result["success"]:
                metrics["solved"] = True
                metrics["final_pass_rate"] = test_result["pass_rate"]
                break

        metrics["total_iterations"] = len(steps)
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, steps, metrics)}


class ConfidenceThresholdPolicy(BasePolicy):
    """Эскалирует если confidence reviewer'а < порога.
    """

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        threshold = self.cfg.get("confidence_threshold", 0.50)  # правка 0.2
        max_iter = budget_cfg.get("max_total_iterations", 7)
        tier = "weak"
        steps = []
        cost = 0.0

        for i in range(1, max_iter + 1):
            code = backend.generate(task.instance_id, tier)
            review = backend.review(task.instance_id, code, tier)
            test_result = self._run_tests(task, code)
            cost_key = {"weak": "weak_call", "strong": "strong_call", "human": "human_call"}[tier]
            cost += costs_cfg.get(cost_key, 1) + costs_cfg.get("review_call", 1) + costs_cfg.get("test_run", 0.5)

            confidence = review.get("confidence", 0.5)

            state_tier = tier
            if test_result["success"]:
                action = "solved"
            elif confidence < threshold and tier == "weak":
                action = "escalate_to_strong"
                tier = "strong"
                metrics["escalated_to_strong"] = True
            elif confidence < threshold and tier == "strong":
                action = "escalate_to_human"
                tier = "human"
                metrics["escalated_to_human"] = True
            else:
                action = f"retry_{tier}"

            step = {
                "step": i,
                "state": {"tier": state_tier, "iteration": i, "confidence": confidence,
                          "cost_so_far": round(cost, 2)},
                "action": action,
                "next_state": {"tier": tier, "pass_rate": test_result["pass_rate"]},
                "reward": 1.0 if test_result["success"] else -0.5,
                "done": test_result["success"],
            }
            steps.append(step)

            if test_result["success"]:
                metrics["solved"] = True
                metrics["final_pass_rate"] = test_result["pass_rate"]
                break

        metrics["total_iterations"] = len(steps)
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, steps, metrics)}


class HumanFallbackPolicy(BasePolicy):
    """Weak → Strong → Human. По одной попытке на тир.

    Правка 0.5: ставим своё имя в trace_record (не RetryThenEscalatePolicy).
    """

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        cfg = {**self.cfg, "max_weak_attempts": 1, "max_strong_attempts": 1}
        result = RetryThenEscalatePolicy(cfg).run_task(task, backend, budget_cfg, costs_cfg)
        # Правка 0.5: подписываем своим именем
        result["trace_record"]["policy"] = self.__class__.__name__
        return result


class RandomPolicy(BasePolicy):
    """Random tier at each step; lower-bound baseline."""

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        import random
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        max_iter = budget_cfg.get("max_total_iterations", 7)
        tiers = ["weak", "strong", "human"]
        steps = []
        cost = 0.0
        task_seed = sum(ord(c) for c in task.instance_id)
        rng = random.Random(self.cfg.get("seed", 42) + task_seed)

        for i in range(1, max_iter + 1):
            tier = rng.choice(tiers)
            code = backend.generate(task.instance_id, tier)
            test_result = self._run_tests(task, code)
            cost_key = {"weak": "weak_call", "strong": "strong_call", "human": "human_call"}[tier]
            cost += costs_cfg.get(cost_key, 1) + costs_cfg.get("test_run", 0.5)

            # Правка 0.6: ставим флаги эскалации
            if tier == "strong":
                metrics["escalated_to_strong"] = True
            if tier == "human":
                metrics["escalated_to_human"] = True

            step = {
                "step": i,
                "state": {"tier": tier, "iteration": i, "cost_so_far": round(cost, 2)},
                "action": f"random_{tier}",
                "next_state": {"pass_rate": test_result["pass_rate"]},
                "reward": 1.0 if test_result["success"] else -0.5,
                "done": test_result["success"],
            }
            steps.append(step)

            if test_result["success"]:
                metrics["solved"] = True
                metrics["final_pass_rate"] = test_result["pass_rate"]
                break

        metrics["total_iterations"] = len(steps)
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, steps, metrics)}


class OraclePolicy(BasePolicy):
    """Offline upper-bound: использует первый тир, который решает задачу."""

    def run_task(self, task, backend, budget_cfg, costs_cfg) -> dict:
        metrics = self._base_metrics(task.instance_id, task.difficulty)
        steps = []
        cost = 0.0

        for i, tier in enumerate(["weak", "strong", "human"], start=1):
            code = backend.generate(task.instance_id, tier)
            test_result = self._run_tests(task, code)
            cost_key = {"weak": "weak_call", "strong": "strong_call", "human": "human_call"}[tier]
            cost += costs_cfg.get(cost_key, 1) + costs_cfg.get("test_run", 0.5)

            if tier == "strong":
                metrics["escalated_to_strong"] = True
            if tier == "human":
                metrics["escalated_to_human"] = True

            step = {
                "step": i,
                "state": {"tier": tier, "iteration": i, "cost_so_far": round(cost, 2)},
                "action": f"oracle_try_{tier}",
                "next_state": {"tier": tier, "pass_rate": test_result["pass_rate"]},
                "reward": 1.0 if test_result["success"] else -0.5,
                "done": test_result["success"],
            }
            steps.append(step)

            if test_result["success"]:
                metrics["solved"] = True
                metrics["final_pass_rate"] = test_result["pass_rate"]
                break

        metrics["total_iterations"] = len(steps)
        metrics["cost_score"] = round(cost, 2)
        return {"metrics": metrics, "trace_record": self._make_trace_record(
            task.instance_id, steps, metrics)}