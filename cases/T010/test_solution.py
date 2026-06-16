# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_norm_basic():
    result = normalize_scores([10,20,30]); assert result == [0.0,0.5,1.0], result

def test_norm_edge():
    result = normalize_scores([5,5,5]); assert result == [0,0,0], result
