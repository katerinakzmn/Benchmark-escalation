# Task Taxonomy

## Purpose

The 120-task dataset is structured along a taxonomy to ensure controlled coverage and prevent hidden biases.
Without a taxonomy it would be impossible to answer: *"Is policy X better because the sample happened to include many easy off-by-one bugs?"*

The taxonomy serves three goals:
1. **Reproducibility** — another researcher can generate an equivalent dataset from the same axes.
2. **Controlled comparison** — experiments can be sliced by individual cells (e.g. logic-error tasks only).
3. **Honest scope** — the taxonomy explicitly states what task types are *not* covered.

---

## Axes

Each task is annotated along five axes stored in `dataset/tasks.json`:

| Axis           | Field in JSON      | Values                                                                                     |
|----------------|--------------------|--------------------------------------------------------------------------------------------|
| Domain         | `domain`           | algorithms, data_structures, string_processing, math, graph, dynamic_programming, oop, system |
| Defect type    | `defect_type`      | logic_error, off_by_one, edge_case, type_error, complexity, data_structure_misuse, recursion_error, algorithm_error |
| Code structure | `structure`        | function, class_method, standalone, recursive                                              |
| Reasoning type | `reasoning_type`   | procedural, structural, analytical, creative                                               |
| Minimum tier   | `min_tier`         | weak, strong, human                                                                        |

`min_tier` is the empirical label: the lowest model tier that consistently solves the task.
It is the primary target variable for escalation analysis.

---

## Dataset Distribution (120 tasks)

| Domain              | Easy | Medium | Hard | Total |
|---------------------|------|--------|------|-------|
| algorithms          |  5   |   10   |  5   |  20   |
| data_structures     |  5   |   10   |  5   |  20   |
| string_processing   |  5   |    8   |  2   |  15   |
| math                |  5   |    5   |  5   |  15   |
| graph               |  5   |    5   |  5   |  15   |
| dynamic_programming |  5   |    5   |  5   |  15   |
| oop                 |  5   |    5   |  0   |  10   |
| system              |  5   |    0   |  5   |  10   |
| **Total**           | **40** | **40** | **40** | **120** |

Difficulty levels: Easy = 40 tasks · Medium = 40 · Hard = 40 (equal split).

---

## Task Generation

All tasks follow **mutation-based generation**:

1. Take a verified reference implementation (passes all tests).
2. Apply exactly **one** mutation operator:

   | Operator            | Example                        |
   |---------------------|--------------------------------|
   | `off_by_one`        | `i < n` → `i <= n`            |
   | `wrong_operator`    | `+` → `-`, `and` → `or`       |
   | `missing_case`      | remove an `else` branch        |
   | `wrong_variable`    | `left` → `right`               |
   | `logic_inversion`   | `if cond` → `if not cond`      |
   | `boundary_skip`     | change a slice boundary index  |
   | `type_mutation`     | `int` → `float`, list → tuple  |

3. Verify that the buggy version fails at least one test (**I₁**) and the reference passes all tests (**I₂**).
4. Record all five axis labels in the task JSON.

One mutation per task → unambiguous ground truth, no alternative correct fixes.

---

## Validation Invariant

Every task must satisfy:

- **I₁ (buggy fails):** `∃ t ∈ T : exec(buggy, t) = FAIL`
- **I₂ (reference passes):** `∀ t ∈ T : exec(reference, t) = PASS`

Tasks failing either invariant are rejected. Checked automatically in CI.

---

## Why This Matters for Escalation Analysis

- **By defect type:** reveals which bug categories benefit most from escalation.
- **By domain:** shows whether certain knowledge areas require the strong model.
- **By min_tier:** lets us measure how well each policy predicts the right escalation level.
  A policy that escalates exactly where `min_tier = strong` or `min_tier = human` is perfectly calibrated.
  The gap between escalation decisions and `min_tier` labels directly quantifies policy inefficiency.