# T006: Bug Report

**Difficulty:** medium

## Problem Statement

`TTLCache` does not expire entries correctly: entries with a short TTL are still returned after expiration.

## Steps to Reproduce

Run the tests:
```bash
pytest test_solution.py
```
