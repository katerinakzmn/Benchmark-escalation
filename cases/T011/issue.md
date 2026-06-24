# T011: Bug Report

**Difficulty:** hard

## Problem Statement

`RateLimiter.is_allowed()` behaves incorrectly: it either blocks requests that should be allowed or allows requests that should be blocked. The sliding window logic appears to be broken.

## Steps to Reproduce

```bash
pytest test_solution.py
```
