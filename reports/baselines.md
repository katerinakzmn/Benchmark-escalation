# Baseline Policy Comparison

**Date:** 2026-06-22 13:10  
**Backend:** `mock`  
**Tasks:** 15

## Results

| Policy | Solved | Solved% | Avg Cost | Avg Iters | Escal to Strong | Escal to Human |
|--------|--------|---------|----------|-----------|-------------|------------|
| `fixed_weak` | 3/15 | 20% | 8.7 | 5.8 | 0% | 0% |
| `fixed_strong` | 8/15 | 53% | 3.5 | 1.0 | 100% | 0% |
| `retry_then_escalate` | 14/15 | 93% | 10.4 | 3.1 | 80% | 47% |
| `progress_heuristic` | 14/15 | 93% | 13.5 | 4.4 | 80% | 47% |
| `confidence_threshold` | 3/15 | 20% | 14.5 | 5.8 | 0% | 0% |
| `human_fallback` | 14/15 | 93% | 9.2 | 2.3 | 80% | 47% |
| `random` | 13/15 | 87% | 11.5 | 2.9 | 0% | 0% |
| `oracle` | 14/15 | 93% | 9.2 | 2.3 | 80% | 47% |

## Best Policy: `retry_then_escalate`

| Difficulty | Count | Solved | Solved% | Avg Cost | Avg Iters |
|------------|-------|--------|---------|----------|-----------|
| easy | 5 | 5 | 100% | 6.6 | 2.4 |
| medium | 5 | 4 | 80% | 11.8 | 3.2 |
| hard | 5 | 5 | 100% | 12.8 | 3.6 |