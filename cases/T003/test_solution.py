# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_pal_basic():
    assert is_palindrome('racecar') is True
    assert is_palindrome('Racecar') is True

def test_pal_edge():
    assert is_palindrome('') is True
    assert is_palindrome('hello') is False
