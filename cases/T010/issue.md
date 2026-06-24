# T010: Bug Report

**Difficulty:** medium

## Problem Statement

`normalize_scores` produces incorrect normalized values. When all scores are equal, the result should be all zeros.

## Steps to Reproduce

Run the tests:
```bash
pytest test_solution.py
```
