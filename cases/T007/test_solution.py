# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_flat_basic():
    assert flatten_dict({'a': {'b': 1}}) == {'a_b': 1}

def test_flat_deep():
    assert flatten_dict({'a': {'b': {'c': 42}}}) == {'a_b_c': 42}
