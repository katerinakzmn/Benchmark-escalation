# T015: Bug Report

**Difficulty:** hard

## Problem Statement

Bug: shortest_path_bfs помечает вершину visited после извлечения, а не при добавлении в очередь.

## Steps to Reproduce

Run the tests:
```bash
pytest test_solution.py
```
