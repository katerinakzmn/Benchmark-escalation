# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_chunk_basic():
    assert chunk_list([1,2,3],2) == [[1,2],[3]]
    assert chunk_list([1,2],5) == [[1,2]]
