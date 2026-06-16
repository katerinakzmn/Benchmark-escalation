# Benchmark for Multi-Agent Software Development Escalation Policies

> A benchmark prototype for evaluating escalation policies in LLM-based software engineering workflows.






***

## Table of Contents

- [Overview](#overview)
- [Goals](#goals)
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Task Format](#task-format)
- [Metrics](#metrics)
- [Baseline Policies](#baseline-policies)
- [Example Trajectory Artifact](#example-trajectory-artifact)
- [Current Limitations](#current-limitations)
- [README Style Upgrade](#readme-style-upgrade)

***

## Overview

This project is a benchmark prototype for evaluating LLM agents and multi-agent workflows in software development tasks. Unlike traditional code-generation benchmarks, it evaluates not only the final outcome, but also the decision-making process itself: when an agent retries, when it escalates to a stronger model, when it runs tests, and when it hands the task off to a human.

Most existing benchmarks focus on the quality of the final code or patch, but pay much less attention to the strategy used along the way. This project introduces a benchmark environment where escalation policies can be compared by quality, cost, time, and trajectory structure.

***

## Goals

The project is designed for:

- Comparing single-agent and multi-agent workflows.
- Evaluating policy control, not only final outcomes.
- Running reproducible toy tasks for fast experimentation.
- Logging decision trajectories in a structured format suitable for later analysis.

***

## Features

- Run the benchmark on a set of toy software engineering tasks.
- Support multiple escalation policies.
- Support multiple backends: `mock`, `openai`, and `gemini`.
- Save trajectories in `state/action/next_state/reward/done` format.
- Compute core benchmark metrics automatically.
- Store run artifacts in separate `runs/` directories.

***

## Repository Structure

```text
benchmark_escalation/
├── agents/
├── backends/
├── dataset/
├── cases/
├── policies/
├── runner/
├── environments/
├── evaluation/
├── configs/
├── runs/
├── docs/
└── reports/
```

***

## Installation

### Requirements

- Python 3.10+
- pip
- virtualenv (recommended)

### Install dependencies

```bash
git clone <repo_url>
cd benchmark_escalation
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

***

## Quick Start

Run the benchmark with the mock backend:

```bash
python -m benchmark_escalation.runner.run_benchmark \
  --dataset toy \
  --backend mock \
  --policy retry_then_escalate \
  --config configs/default.yaml
```

After execution, results are stored in a directory like this:

```text
runs/run_YYYY_MM_DD_NNN/
├── config.json
├── traces.json
├── metrics.json
└── summary.md
```

***

## Task Format

At the first stage, the benchmark uses toy tasks in JSON format. Each task contains:

- `task_id`
- `task_type`
- `difficulty`
- `problem_statement`
- `original_code`
- `entry_point`
- `tests`
- `reference_solution`
- `oracle_label`

In future versions, the project may move to file-based cases with separate files such as `issue.md`, `solution.py`, `test_solution.py`, and `metadata.yaml`.

***

## Metrics

Core benchmark metrics include:

- `solved_rate`
- `final_pass_rate`
- `cost_to_green`
- `time_to_green`
- `num_iterations`
- `num_test_runs`
- `escalation_to_strong_rate`
- `human_escalation_rate`
- `policy_regret`

These metrics make it possible to evaluate both result quality and the efficiency of the decision strategy itself.

***

## Baseline Policies

The benchmark is intended to compare the following baseline policies:

- `fixed_weak`
- `fixed_strong`
- `retry_then_escalate`
- `confidence_threshold`
- `progress_heuristic`
- `human_fallback`
- `random`
- `oracle`

***

## Example Trajectory Artifact

```json
{
  "episode_id": "run_007_T002",
  "task_id": "T002",
  "step": 2,
  "state": {
    "current_tier": "weak",
    "iteration": 2,
    "pass_rate_prev": 0.33,
    "confidence": 0.42,
    "cost_so_far": 2.5
  },
  "action": "switch_to_strong",
  "next_state": {
    "current_tier": "strong",
    "iteration": 3,
    "cost_so_far": 5.5
  },
  "reward": -3.0,
  "done": false
}
```

***

## Current Limitations

The current version is a prototype and is still focused on toy tasks. Support for repository-level tasks, secure execution isolation, Docker-based evaluation, and integration with real bug benchmarks is considered the next stage of development.
