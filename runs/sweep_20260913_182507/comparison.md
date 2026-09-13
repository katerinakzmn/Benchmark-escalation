# Comparison of policy escalation

**Sweep:** `20260913_182507`  
**Backend:** `polza`  
**Date:** 2026-09-13 19:14  
**Git:** `f20e694`

## Main table

| Policy | Solve rate | Avg cost (USD) | Median cost | Avg iter | Strong esc % | Human esc % | Utility |
|--------|-----------|----------------|-------------|----------|-------------|------------|---------|
| fixed_weak | 90.0% | ₽0.0143 | ₽0.0143 | 1.43 | 0.0% | 0.0% | 0.8999 |
| fixed_strong | 93.3% | ₽0.1673 | ₽0.1673 | 1.00 | 100.0% | 0.0% | 0.9317 |
| retry_then_escalate | 96.7% | ₽0.0314 | ₽0.0314 | 1.25 | 10.8% | 3.3% | 0.9664 |
| confidence_threshold | 89.2% | ₽0.0144 | ₽0.0144 | 1.46 | 0.0% | 0.0% | 0.8915 |
| progress_heuristic | 96.7% | ₽0.0340 | ₽0.0340 | 1.38 | 10.8% | 3.3% | 0.9663 |
| oracle | 96.7% | ₽0.0337 | ₽0.0337 | 1.15 | 10.8% | 4.2% | 0.9663 |