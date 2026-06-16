# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_rl_basic():
    rl = RateLimiter(max_calls=3, window_seconds=10); results=[rl.is_allowed() for _ in range(4)]; assert results == [True,True,True,False], results

def test_rl_window():
    import time as _t
    rl = RateLimiter(max_calls=2, window_seconds=0.1)
    assert rl.is_allowed()
    assert rl.is_allowed()
    assert not rl.is_allowed()
    _t.sleep(0.15)
    assert rl.is_allowed()
