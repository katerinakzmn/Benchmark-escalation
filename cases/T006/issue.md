# T006: Bug Report

**Difficulty:** medium

## Problem Statement

Bug: TTLCache.get() неверно проверяет истечение записи. Нужно if time.time() - ts > self.ttl.

## Steps to Reproduce

Run the tests:
```bash
pytest test_solution.py
```
