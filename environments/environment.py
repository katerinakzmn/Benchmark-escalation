"""
The test execution environment for a single benchmark task.
Runs each test in a separate thread with a timeout (default is 5 seconds).
"""

import threading
from dataclasses import dataclass
from typing import List

from tasks import Task


@dataclass
class StepResult:
    step_number:     int
    model_used:      str
    code_generated:  str
    tests_total:     int
    tests_passed:    int
    tests_failed:    int
    failure_reasons: List[str]
    pass_rate:       float
    success:         bool


def _run_test_with_timeout(test_fn, code: str, timeout: float = 5.0) -> dict:
    result: dict = {}

    def target():
        result.update(test_fn(code))

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        return {"passed": False, "reason": "timeout"}

    return result if result else {"passed": False, "reason": "no result returned"}


class Environment:
    TEST_TIMEOUT = 5.0

    def __init__(self, task: Task):
        self.task = task

    def run(self, code: str, model_used: str, step_number: int) -> StepResult:
        passed  = 0
        failed  = 0
        reasons = []

        timed_out = False

        for test_fn in self.task.tests:
            result = _run_test_with_timeout(test_fn, code, timeout=self.TEST_TIMEOUT)
            if result["passed"]:
                passed += 1
            else:
                failed += 1
                reason = result["reason"]
                reasons.append(f"[{test_fn.__name__}] {reason}")
                if "timeout" in reason:
                    timed_out = True
                    break

        total     = len(self.task.tests)
        pass_rate = passed / total if total > 0 else 0.0

        return StepResult(
            step_number    = step_number,
            model_used     = model_used,
            code_generated = code,
            tests_total    = total,
            tests_passed   = passed,
            tests_failed   = failed + (total - passed - failed),
            failure_reasons= reasons,
            pass_rate      = pass_rate,
            success        = (failed == 0 and not timed_out),
        )