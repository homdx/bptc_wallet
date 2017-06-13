from collections import defaultdict
from toposort import toposort_flatten


def divide_rounds(self, events):
    """Restore invariants for `can_see`, `witnesses` and `round`.

    :param self: Hashgraph
    :param events: Topologically sorted sequence of new event to process.
    """

    graph = {}
    for event_id, event in events.items():
        parents = set()
        if event.parents.self_parent:
            parents.add(event.parents.self_parent)
        if event.parents.other_parent:
            parents.add(event.parents.other_parent)
        graph[event.id] = parents

    for event_id in reversed(list(toposort_flatten(graph))):
        event = events[event_id]
        # Check if this is a root event or not
        if event.parents == (None, None):
            # This is a root event
            event.round = 0
            self.witnesses[0][event.verify_key] = event
            event.can_see = {event.verify_key: event}
        else:
            # This is a normal event
            # Estimate round (= maximum round of parents)
            # logger.info("Checking {}".format(str(event.parents)))
            calculated_round = 0
            for parent in event.parents:
                if parent is not None and self.lookup_table[parent].round > calculated_round:
                    calculated_round = self.lookup_table[parent].round

            # recurrence relation to update can_see
            p0 = self.lookup_table[
                event.parents.self_parent].can_see if event.parents.self_parent is not None else dict()
            p1 = self.lookup_table[
                event.parents.other_parent].can_see if event.parents.other_parent is not None else dict()
            event.can_see = {c: self.get_higher(p0.get(c), p1.get(c))
                             for c in p0.keys() | p1.keys()}

            # Count distinct paths to distinct nodes
            # TODO: What exactly happens here? Why two levels of visible events?
            hits = defaultdict(int)
            for verify_key, visible_event in event.can_see.items():
                if visible_event.round == calculated_round:
                    for c_, k_ in visible_event.can_see.items():
                        if k_.round == calculated_round:
                            hits[c_] += self.known_members[verify_key].stake

            # check if i can strongly see enough events
            if sum(1 for x in hits.values() if x > self.supermajority_stake) > self.supermajority_stake:
                event.round = calculated_round + 1
            else:
                event.round = calculated_round

            # Events can always see themselves
            event.can_see[event.verify_key] = event

            # An event becomes a witness if it is the first of that round
            if event.round > self.lookup_table[event.parents.self_parent].round:
                self.witnesses[event.round][event.verify_key] = event
