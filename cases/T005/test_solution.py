# Tests for the case implementation.
from original_code import *

def test_max_basic():
    assert find_max([1,5,3]) == 5
    assert find_max([-10,-3,-7]) == -3
