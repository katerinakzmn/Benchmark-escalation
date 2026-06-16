# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_vowels_basic():
    assert count_vowels('hello') == 2
    assert count_vowels('AEIOU') == 5

def test_vowels_edge():
    assert count_vowels('') == 0
    assert count_vowels('bcdfg') == 0
