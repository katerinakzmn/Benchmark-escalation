# Comparison of policy escalation

**Sweep:** `20260913_171300`  
**Backend:** `polza`  
**Date:** 2026-09-13 18:02  
**Git:** `f20e694`

## Main table

| Policy | Solve rate | Avg cost (USD) | Median cost | Avg iter | Strong esc % | Human esc % | Utility |
|--------|-----------|----------------|-------------|----------|-------------|------------|---------|
| fixed_weak | 90.0% | ₽0.0140 | ₽0.0140 | 1.42 | 0.0% | 0.0% | 0.8999 |
| fixed_strong | 90.8% | ₽0.1685 | ₽0.1685 | 1.00 | 100.0% | 0.0% | 0.9066 |
| retry_then_escalate | 94.2% | ₽0.0361 | ₽0.0361 | 1.29 | 11.7% | 5.8% | 0.9413 |
| confidence_threshold | 90.0% | ₽0.0141 | ₽0.0141 | 1.43 | 0.0% | 0.0% | 0.8999 |
| progress_heuristic | 94.2% | ₽0.0374 | ₽0.0374 | 1.41 | 10.8% | 5.0% | 0.9413 |
| oracle | 96.7% | ₽0.0329 | ₽0.0329 | 1.16 | 10.8% | 5.0% | 0.9663 |