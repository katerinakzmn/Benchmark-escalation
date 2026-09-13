## Experiment Protocol: Real-LLM Evaluation of Escalation Policies



## Models

| Tier   | Model          | In (per 1M tok) | Out (per 1M tok) | 
|--------|----------------|-----------------|------------------|
| weak   | gpt-4o-mini    | $0.15           | $0.60            |
| strong | gpt-4o         | $2.50           | $10.00           | 


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


