# Experiment Protocol: Real-LLM Evaluation of Escalation Policies

## Research Question

**Which escalation policy achieves the best quality/cost trade-off when using real LLMs on bug-fixing tasks?**

Sub-questions:
- **RQ1** — Does the weak-to-strong solve_rate gap vary by defect type and difficulty?
- **RQ2** — At what confidence threshold does the escalation policy match Oracle utility?
- **RQ3** — What is the minimum strong-escalation rate to stay within 2 pp of FixedStrong?

---

## Winner Criterion

Fixed before the run. The preferred policy is the **cheapest policy whose solve_rate is no more than 2 pp below the maximum**:

```
S_max = max{ S(π) }
Admissible = { π : S(π) ≥ S_max − 0.02 }
π* = argmin{ C(π) : π ∈ Admissible }
```

Tie-break: lowest `avg_iterations`.

---

## Models

| Tier   | Model          | In (per 1M tok) | Out (per 1M tok) | Role                        |
|--------|----------------|-----------------|------------------|-----------------------------|
| weak   | gpt-4o-mini    | $0.15           | $0.60            | Fast, cheap; handles Easy   |
| strong | gpt-4o         | $2.50           | $10.00           | High quality; handles Hard  |
| human  | simulated      | $0.50 / task    | —                | Returns reference solution  |

The human tier is a deterministic oracle returning the reference solution — it is an upper bound for `HumanFallback`, not a real participant.

---

## Policies

| Policy               | Type        | Logic                                                       |
|----------------------|-------------|-------------------------------------------------------------|
| FixedWeak            | baseline    | All tasks go to the weak model; no escalation               |
| FixedStrong          | baseline    | All tasks go to the strong model; no escalation             |
| RetryThenEscalate    | adaptive    | Weak tries up to N times; escalates to strong on failure    |
| ConfidenceThreshold  | adaptive    | Escalates if weak self-reported confidence < θ              |
| ProgressHeuristic    | adaptive    | Escalates if progress between iterations < ε over k steps  |
| Oracle               | upper bound | Uses the minimum tier that solves each task (ground truth)  |

> `HumanFallback` is available for manual runs but excluded from the main sweep because the simulated human tier gives an inflated upper bound.

**Default parameters:** RetryThenEscalate N=3 · ConfidenceThreshold θ=0.7 · ProgressHeuristic k=2, ε=0.05

---

## Metrics

**Primary**

| Metric          | Definition                                     |
|-----------------|------------------------------------------------|
| `solve_rate`    | Fraction of tasks passing all tests            |
| `avg_cost_usd`  | Mean cost per task (USD)                       |

**Secondary**

| Metric                    | Definition                                     |
|---------------------------|------------------------------------------------|
| `avg_iterations`          | Mean agent calls per task                      |
| `strong_escalation_rate`  | Fraction escalated to strong                   |
| `utility`                 | `−0.01 · avg_cost_usd + 1.0 · solve_rate`     |
| `regret`                  | `solve_rate(Oracle) − solve_rate(π)`           |

Statistical tests: McNemar (solve_rate), Wilcoxon (avg_cost), α = 0.05.

---

## Run Configuration

| Parameter              | Value  | Reason                          |
|------------------------|--------|---------------------------------|
| `temperature`          | 0      | Reproducibility                 |
| `max_tokens`           | 2048   | Sufficient for a typical patch  |
| `max_cost_usd_per_task`| $0.10  | Hard per-task budget cap        |

All policies share the same system prompt:

```
You are a software debugging assistant. You will be given a Python function with a single bug.
Your task is to identify the bug and return the corrected version of the entire function.
Return only the corrected code, no explanations. Do not change the function signature.
```

---

## Limitations

| Threat                  | Mitigation                                                        |
|-------------------------|-------------------------------------------------------------------|
| Dataset bias (Python only) | Scope results explicitly to Python algorithmic debugging       |
| Model contamination     | Tasks are authored or mutated; not published before the run      |
| API price changes       | Token counts logged; costs re-calculable at any price point      |
| API nondeterminism      | temperature=0; results are single-run (no majority vote)         |
| Simulated human tier    | Clearly labeled as theoretical upper bound, not real expert data |