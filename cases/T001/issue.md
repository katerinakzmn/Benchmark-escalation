# T001: Bug Report

**Difficulty:** easy

## Problem Statement

Bug: sum_positive пропускает последний элемент списка. Нужно range(len(numbers)) вместо range(len(numbers)-1).

## Steps to Reproduce

Run the tests:
```bash
pytest test_solution.py
```
