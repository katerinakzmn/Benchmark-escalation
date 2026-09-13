# Task Taxonomy


Each task is annotated along five axes stored in `dataset/tasks.json`:

| Axis           | Field in JSON      | Values                                                                                     |
|----------------|--------------------|--------------------------------------------------------------------------------------------|
| Domain         | `domain`           | algorithms, arrays, data_structures, dicts, numeric, oop, parsing, string |
| Defect type    | `defect_type`      | boundary_case, exception_handling, missing_sort, missing_update, off_by_one, specification, state_mutation, wrong_condition, wrong_logic, wrong_operator, wrong_return |
| Code structure | `structure`        | function, class_method, standalone, recursive                                              |
| Reasoning type | `reasoning_type`   | procedural, structural, analytical, creative                                               |
| Minimum tier   | `min_tier`         | weak, strong, human                                                                        |

`min_tier` is the empirical label: the lowest model tier that consistently solves the task.
It is the primary target variable for escalation analysis.

---

## Task Generation

All tasks follow **mutation-based generation**:

1. Take a verified reference implementation (passes all tests).
2. Apply exactly **one** mutation operator:

   | Operator            | Example                        |
   |---------------------|--------------------------------|
   | `off_by_one`        | `i < n` to `i <= n`            |
   | `wrong_operator`    | `+` → `-`, `and` → `or`        |
   | `missing_case`      | remove an `else` branch        |
   | `wrong_variable`    | `left` to `right`              |
   | `logic_inversion`   | `if cond` to `if not cond`     |
   | `boundary_skip`     | change a slice boundary index  |
   | `type_mutation`     | `int` to`float`, list to tuple |

3. Verify that the buggy version fails at least one test (**I₁**) and the reference passes all tests (**I₂**).
4. Record all five axis labels in the task JSON.

One mutation per task → unambiguous ground truth, no alternative correct fixes.

---

## Validation Invariant

Every task must satisfy:

- **I₁ (buggy fails):** `∃ t ∈ T : exec(buggy, t) = FAIL`
- **I₂ (reference passes):** `∀ t ∈ T : exec(reference, t) = PASS`

Tasks failing either invariant are rejected. Checked automatically in CI.
