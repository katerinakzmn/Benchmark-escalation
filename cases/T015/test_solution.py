# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_bfs_basic():
    g={'A':['B','C'],'B':['D'],'C':['D'],'D':[]}
    assert shortest_path_bfs(g,'A','D') == 2

def test_bfs_unreachable():
    assert shortest_path_bfs({'A':['B'],'B':[],'C':[]},'A','C') == -1
