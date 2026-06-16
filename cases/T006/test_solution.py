# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_ttl_basic():
    cache = TTLCache(ttl=60); cache.set('x',42); assert cache.get('x') == 42

def test_ttl_expired():
    cache = TTLCache(ttl=0); cache.set('x',42); assert cache.get('x') is None
