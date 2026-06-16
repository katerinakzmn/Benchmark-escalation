"""Генерирует cases/TXXX/ из dataset/tasks.json"""
import json, os

DATASET = os.path.join("dataset", "tasks.json")
CASES_DIR = "cases"

ORACLE_LABELS = {
    "easy":   "weak",
    "medium": "strong",
    "hard":   "strong",
}

BUG_TYPES = {
    "T001": "off_by_one",       "T002": "logic_error",
    "T003": "case_sensitivity", "T004": "missing_reverse",
    "T005": "wrong_builtin",    "T006": "ttl_expiration",
    "T007": "string_concat",    "T008": "wrong_builtin",
    "T009": "off_by_one",       "T010": "normalization",
    "T011": "rate_limit",       "T012": "lru_order",
    "T013": "missing_sort",     "T014": "increment_vs_decrement",
    "T015": "visited_order",
}

def assertions_to_pytest(tests: list, task_id: str) -> str:
    lines = [
        "# auto-generated from dataset/tasks.json",
        "# pytest test_solution.py",
        "",
    ]
    for test in tests:
        lines.append(f"def {test['name']}():")
        for a in test.get("assertions", []):
            if a.get("custom"):
                for code_line in a["code"].splitlines():
                    lines.append(f"    {code_line}")
        lines.append("")
    return "\n".join(lines)


with open(DATASET, encoding="utf-8") as f:
    tasks = json.load(f)

for task in tasks:
    tid = task["instance_id"]
    out = os.path.join(CASES_DIR, tid)
    os.makedirs(out, exist_ok=True)

    # issue.md
    with open(os.path.join(out, "issue.md"), "w", encoding="utf-8") as f:
        f.write(f"# {tid}: Bug Report\n\n")
        f.write(f"**Difficulty:** {task['difficulty']}\n\n")
        f.write(f"## Problem Statement\n\n{task['problem_statement']}\n\n")
        f.write("## Steps to Reproduce\n\nRun the tests:\n```bash\npytest test_solution.py\n```\n")

    # original_code.py
    with open(os.path.join(out, "original_code.py"), "w", encoding="utf-8") as f:
        f.write(f"# {tid} — original buggy code\n\n")
        f.write(task["original_code"])

    # test_solution.py
    with open(os.path.join(out, "test_solution.py"), "w", encoding="utf-8") as f:
        f.write(assertions_to_pytest(task["tests"], tid))

    # metadata.yaml
    oracle_label = ORACLE_LABELS.get(task["difficulty"], "strong")
    bug_type = BUG_TYPES.get(tid, "unknown")
    test_names = [t["name"] for t in task["tests"]]
    with open(os.path.join(out, "metadata.yaml"), "w", encoding="utf-8") as f:
        f.write(f"task_id: {tid}\n")
        f.write(f"difficulty: {task['difficulty']}\n")
        f.write(f"bug_type: {bug_type}\n")
        f.write(f"oracle_min_tier: {oracle_label}\n")
        f.write(f"repro_command: pytest test_solution.py -q\n")
        f.write(f"tags:\n  - {bug_type}\n  - {task['difficulty']}\n")
        f.write(f"tests:\n")
        for name in test_names:
            f.write(f"  - {name}\n")

    print(f"  ✓ cases/{tid}/")

print(f"\nДонe: {len(tasks)} задач → cases/")