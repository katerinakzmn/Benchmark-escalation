# Tests for the case implementation.
from original_code import *

def test_chunk_basic():
    assert chunk_list([1,2,3],2) == [[1,2],[3]]
    assert chunk_list([1,2],5) == [[1,2]]
