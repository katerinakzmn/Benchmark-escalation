# Tests for the case implementation.
from original_code import *

def test_merge_sorted():
    assert merge_intervals([[1,3],[2,6],[8,10]]) == [[1,6],[8,10]]

def test_merge_unsorted():
    assert merge_intervals([[8,10],[1,3],[2,6]]) == [[1,6],[8,10]]
