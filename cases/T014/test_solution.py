# auto-generated from dataset/tasks.json
# pytest test_solution.py

def test_topo_basic():
    g={'A':['B','C'],'B':['D'],'C':['D'],'D':[]}
    order=topological_sort(g)
    assert order[0]=='A' and order[-1]=='D' and set(order)=={'A','B','C','D'}

def test_topo_chain():
    assert topological_sort({'X':['Y'],'Y':['Z'],'Z':[]}) == ['X','Y','Z']
