# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_rev_basic():
    assert reverse_words('one two three') == 'three two one'

def test_rev_edge():
    assert reverse_words('  a   b  ') == 'b a'
