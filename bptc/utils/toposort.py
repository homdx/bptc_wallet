from toposort import toposort_flatten


def toposort(events):
    """Return a topological sorted list of events."""
    graph = {}
    for event_id, event in events.items():
        if event.parents.self_parent in events:
            self_parent = event.parents.self_parent
        else:
            self_parent = None
        if event.parents.other_parent in events:
            other_parent = event.parents.other_parent
        else:
            other_parent = None
        parents = set([self_parent, other_parent])
        graph[event.id] = parents - set([None])  # Remove empty entries

    return [events[event_id] for event_id in toposort_flatten(graph)]
