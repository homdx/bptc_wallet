from collections import defaultdict, namedtuple
from functools import reduce

from libnacl.encode import base64_decode
from toposort import toposort_flatten

from bptc.utils import bfs

C = 6  # How often a coin round occurs, e.g. 6 for every sixth round


def divide_rounds(hashgraph, events):
    """Restore invariants for `can_see`, `witnesses` and `round`.

    :param hashgraph: Hashgraph
    :param events: Topologically sorted sequence of new event to process.
    """

    graph = {}
    for event_id, event in events.items():
        parents = set([event.parents.self_parent, event.parents.other_parent])
        graph[event.id] = parents - set([None])  # Remove empty entries

    for event_id in reversed(toposort_flatten(graph)):
        event = hashgraph.lookup_table[event_id]
        # Check if this is a root event or not
        if event.parents == (None, None):
            # This is a root event
            event.round = 0
            hashgraph.witnesses[0][event.verify_key] = event
            event.can_see = {event.verify_key: event}
        else:
            # This is a normal event
            # utils.logger.info("Checking {}".format(str(event.parents)))
            # Estimate round (= maximum round of parents)
            calculated_round = max([hashgraph.lookup_table[parent].round
                                    for parent in event.parents if parent is not None])

            # recurrence relation to update can_see
            empty_event = namedtuple("Event", ["can_see"])(dict())
            p0 = hashgraph.lookup_table.get(event.parents.self_parent, empty_event).can_see
            p1 = hashgraph.lookup_table.get(event.parents.other_parent, empty_event).can_see
            event.can_see = {c: hashgraph.get_higher(p0.get(c), p1.get(c))
                             for c in p0.keys() | p1.keys()}

            # Count distinct paths to distinct nodes
            # TODO: What exactly happens here? Why two levels of visible events?
            '''
                My guess(Thomas):
                Generates a counter which is required for checking if i can
                strongly see enough events. Therefore these two loops check
                each path which ends in i by looking at the visible events
                of the visible events of i. It sums up for each event which
                can be seen indirectly through another "intermediate" event
                the stake values of all "intermediate" events of all paths
                reaching this event.

                This might be a bug, because it assumes that you only have
                to go two steps back (if there are only 2 nodes it would be
                fine).
            '''
            hits = defaultdict(int)
            for verify_key, visible_event in event.can_see.items():
                if visible_event.round == calculated_round:
                    for c_, k_ in visible_event.can_see.items():
                        if k_.round == calculated_round:
                            hits[c_] += hashgraph.known_members[verify_key].stake

            # check if i can strongly see enough events
            if sum(x > hashgraph.supermajority_stake for x in hits.values()) > hashgraph.supermajority_stake:
                event.round = calculated_round + 1
            else:
                event.round = calculated_round

            # Events can always see themselves
            event.can_see[event.verify_key] = event

            # An event becomes a witness if it is the first of that round
            if event.round > hashgraph.lookup_table[event.parents.self_parent].round:
                hashgraph.witnesses[event.round][event.verify_key] = event


def decide_fame(hashgraph):
    max_r = max(hashgraph.witnesses or [0])
    max_c = 0
    while max_c in hashgraph.consensus:
        max_c += 1

    # helpers to keep code clean
    def iter_undetermined(r_):
        for r in range(max_c, r_):
            if r not in hashgraph.consensus:
                for w in hashgraph.witnesses[r].values():
                    if w not in hashgraph.famous:
                        yield r, w

    def iterate_witnesses():
        """
        A Generator for all witnesses that need to be handled
        :return: A Generator for all witnesses that need to be handled
        """
        # For every round that has to be handled ...
        for round in range(max_c + 1, max_r + 1):
            # ... iterate over the witnesses of that round ...
            for witness in hashgraph.witnesses[round].values():
                # ... and yield (round, witness)
                yield round, witness

    done = set()

    # Iterate over all unhandled witnesses
    for round, witness in iterate_witnesses():  # type: int, Event

        hits = defaultdict(int)
        for c, k in witness.can_see.items():
            if k.round == round - 1:
                for c_, k_ in k.can_see.items():
                    if k_.round == round - 1:
                        hits[c_] += hashgraph.known_members[c].stake
        s = {hashgraph.witnesses[round - 1][c] for c, n in hits.items()
             if n > hashgraph.supermajority_stake}

        for r, x in iter_undetermined(round):
            if round - r == 1:
                witness.votes[x] = x in s
            else:
                filtered_s = filter(lambda w: w in hashgraph.lookup_table, s)  # TODO: check why filtering is necessary
                v, t = majority((hashgraph.known_members[hashgraph.lookup_table[w].verify_key].stake, w.votes[x]) for w in filtered_s)
                if (round - r) % C != 0:
                    if t > hashgraph.supermajority_stake:
                        hashgraph.famous[x] = v
                        done.add(r)
                    else:
                        witness.votes[x] = v
                else:
                    if t > hashgraph.supermajority_stake:
                        witness.votes[x] = v
                    else:
                        # the 1st bit is same as any other bit right? # TODO not!
                        witness_signature_byte = base64_decode(witness.signature.encode("UTF-8"))
                        witness.votes[x] = bool(witness_signature_byte[0] // 128)

    new_c = {r for r in done
             if all(w in hashgraph.famous for w in hashgraph.witnesses[r].values())}
    hashgraph.consensus |= new_c
    return new_c


def find_order(self, new_c):
    def to_int(x):
        return int.from_bytes(self.lookup_table[x].signature, byteorder='big')

    for r in sorted(new_c):
        f_w = {w for w in self.witnesses[r].values() if self.famous[w]}
        white = reduce(lambda a, b: a ^ to_int(b), f_w, 0)
        ts = {}
        seen = set()
        for x in bfs(filter(self.unordered_events.__contains__, f_w),
                     lambda u: (p for p in self.lookup_table[u].parents if p in self.unordered_events)):
            c = self.lookup_table[x].verify_key
            s = {w for w in f_w if c in w.can_see
                 and self.is_higher(w.can_see[c], x)}
            if sum(self.known_members[self.lookup_table[w].verify_key].stake for w in s) > self.total_stake / 2:
                self.unordered_events.remove(x)
                seen.add(x)
                times = []
                for w in s:
                    a = w
                    while (c in a.can_see
                           and self.is_higher(a.can_see[c], x)
                           and self.lookup_table[a].parents):
                        a = self.lookup_table[a].p[0]
                    times.append(self.lookup_table[a].t)
                times.sort()
                ts[x] = .5 * (times[len(times) // 2] + times[(len(times) + 1) // 2])
        final = sorted(seen, key=lambda x: (ts[x], white ^ to_int(x)))
        for i, x in enumerate(final):
            self.idx[x] = i + len(self.ordered_events)
        self.ordered_events += final
    if self.consensus:
        print(self.consensus)


def majority(it):
    hits = [0, 0]
    for s, x in it:
        hits[int(x)] += s
    if hits[0] > hits[1]:
        return False, hits[0]
    else:
        return True, hits[1]
