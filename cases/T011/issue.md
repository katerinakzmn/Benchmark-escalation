# T011: Bug Report

**Difficulty:** hard

## Problem Statement

Bug: RateLimiter.is_allowed() использует now + window (BUG1) и неправильное условие > cutoff вместо < cutoff (BUG2).

## Steps to Reproduce

Run the tests:
```bash
pytest test_solution.py
```
