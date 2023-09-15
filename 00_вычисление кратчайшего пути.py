import collections

def dijkstra(g, source, dest) :
    d  = {}
    p = {}

    visited = []
    to_visit = collections.deque([source])

    while len(to_visit) > 0 :
        v = to_visit.pop()

        

