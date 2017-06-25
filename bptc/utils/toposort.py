from toposort import toposort_flatten


def toposort(hashgraph, events):
    # convert dict of events to adjacent dict
    graph = {}
    for event_id, event in events.items():
        parents = set([event.parents.self_parent, event.parents.other_parent])
        graph[event.id] = parents - set([None])  # Remove empty entries

    return [hashgraph.lookup_table[event_id] for event_id in toposort_flatten(graph)]
