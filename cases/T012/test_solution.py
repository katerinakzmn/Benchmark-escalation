# Tests for the case implementation.
from original_code import *

def test_lru_basic():
    c = LRUCache(2); c.put(1,1); c.put(2,2); assert c.get(1) == 1

def test_lru_eviction():
    c = LRUCache(2)
    c.put(1,1); c.put(2,2)
    c.get(1)
    c.put(3,3)
    assert c.get(2) == -1
    assert c.get(1) == 1
