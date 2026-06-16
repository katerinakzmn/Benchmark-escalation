# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_sum_basic():
    assert sum_positive([1,2,3]) == 6
    assert sum_positive([-1,2,-3,4]) == 6

def test_sum_edge():
    assert sum_positive([]) == 0
    assert sum_positive([5]) == 5
