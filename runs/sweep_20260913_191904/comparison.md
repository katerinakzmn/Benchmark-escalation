# Comparison of policy escalation

**Sweep:** `20260913_191904`  
**Backend:** `polza`  
**Date:** 2026-09-13 20:09  
**Git:** `f20e694`

## Main table

| Policy | Solve rate | Avg cost (USD) | Median cost | Avg iter | Strong esc % | Human esc % | Utility |
|--------|-----------|----------------|-------------|----------|-------------|------------|---------|
| fixed_weak | 86.7% | ₽0.0142 | ₽0.0142 | 1.44 | 0.0% | 0.0% | 0.8665 |
| fixed_strong | 90.8% | ₽0.1739 | ₽0.1739 | 1.00 | 100.0% | 0.0% | 0.9066 |
| retry_then_escalate | 95.8% | ₽0.0392 | ₽0.0392 | 1.30 | 11.7% | 5.8% | 0.9579 |
| confidence_threshold | 88.3% | ₽0.0151 | ₽0.0151 | 1.49 | 0.0% | 0.0% | 0.8832 |
| progress_heuristic | 95.8% | ₽0.0378 | ₽0.0378 | 1.40 | 11.7% | 4.2% | 0.9580 |
| oracle | 94.2% | ₽0.0397 | ₽0.0397 | 1.20 | 13.3% | 6.7% | 0.9413 |