# Tests for the case implementation.
from original_code import *

def test_vowels_basic():
    assert count_vowels('hello') == 2
    assert count_vowels('AEIOU') == 5

def test_vowels_edge():
    assert count_vowels('') == 0
    assert count_vowels('bcdfg') == 0
