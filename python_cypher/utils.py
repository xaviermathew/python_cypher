import networkx as nx
from itertools import islice


def window(seq, n=2):
    "Returns a sliding window (of width n) over data from the iterable"
    "   s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...                   "
    it = iter(seq)
    result = tuple(islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


def get_all_paths(G, min_path_length=None, max_path_length=None):
    if min_path_length is None:
        min_path_length = 1
    if max_path_length is None:
        min_path_length = float('infinity')
    roots = []
    leaves = []
    for node in G.nodes:
        if G.in_degree(node) == 0:
            roots.append(node)
        elif G.out_degree(node) == 0:
            leaves.append(node)

    for root in roots:
        for leaf in leaves:
            for path in nx.all_simple_paths(G, root, leaf):
                if len(path) >= min_path_length:
                    for n in range(min_path_length, min(len(path), max_path_length) + 1):
                        yield from window(path, n)
