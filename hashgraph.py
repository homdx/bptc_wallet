from collections import defaultdict
from event import Event
import logging
from utils import bfs
from itertools import zip_longest
from functools import reduce

C = 6  # what is this?


class Hashgraph:
    def __init__(self):
        self.stake = None
        self.tot_stake = None
        self.min_s = None  # min stake amount

        # {event-hash => event}: this is the hash graph
        self.lookup_table = {}

        # event-hash: latest event from me
        self.head = None

        # {event-hash => round-num}: assigned round number of each event
        # self.round = {}

        # {event-hash}: events for which final order remains to be determined
        self.tbd = set()

        # [event-hash]: final order of the transactions
        self.transactions = []

        self.idx = {}

        # {round-num}: rounds where fame is fully decided
        self.consensus = set()

        # {event-hash => {event-hash => bool}}
        # self.votes = defaultdict(dict)

        # {round-num => {member-pk => event-hash}}:
        self.witnesses = defaultdict(dict)

        self.famous = {}

        # {event-hash => int}: 0 or 1 + max(height of parents)
        # self.height = {}

        # {event-hash => {member-pk => event-hash}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see
        # self.can_see = {}

    def add_first_event(self, event):
        self.add_event(event)
        event.round = 0  # TODO move to event creation ?
        self.witnesses[0][event.verify_key] = event
        event.can_see = {event.verify_key: event}  # TODO move to event creation ?
        self.head = event

    def add_event(self, event: Event):
        """Add given event to this hashgraph."""
        h = event.id
        self.lookup_table[h] = event
        self.tbd.add(h)  # TODO add event?

        logging.info("{}.add_event: {}".format(self, event))

    def set_stake(self, stake):
        self.stake = stake
        self.tot_stake = sum(stake.values())
        self.min_s = 2 * self.tot_stake / 3  # min stake amount

    def create_first_event(self, signing_key):
        event = self._new_event(None, (), signing_key)
        return event

    def new_event(self, payload, other_parent, creator_id):
        event = self._new_event(payload, (self.head, other_parent), creator_id)
        return event

    def _new_event(self, d, parents, signing_key):
        """Create a new event.
        Access hash from class.
        :param creator_id: """
        # TODO: fail if an ancestor of p[1] from creator self.pk is not an ancestor of p[0] ???
        event = Event(signing_key, d, parents)
        logging.info("{}._new_event: {}".format(self, event))
        return event

    def is_valid_event(self, id, event: Event):
        try:
            event.verify_key.verify(event.body, event.signature)
        except ValueError:
            return False

        return (event.id == id
                and (event.parents == ()
                     or (len(event.parents) == 2
                         and event.parents[0].id in self.lookup_table and event.parents[1].id in self.lookup_table
                         and event.parents[0].verify_key == event.verify_key
                         and event.parents[1].verify_key != event.verify_key)))

        # TODO: check if there is a fork (rly need reverse edges?)
        # and all(x.verify_key != ev.verify_key
        #        for x in self.preds[ev.parents[0]]))))

    def get_fingerprint(self):
        """Returns dict of heights for each branch (== HashgraghNetNode)."""
        return {branch_id: event.height for branch_id, event in self.head.can_see.items()}

    def keys(self):
        return self.lookup_table.keys()

    def difference(self, info):
        """Difference with given hashgraph info (fingerprint?)"""

        # NOTE we need bfs() due to cheating possibility -- several children of one parent
        # succ = lambda u: (p for p in u.parents
        #                if (p.verify_key not in info) or (p.height > info[p.verify_key]))
        def succ(u):
            return [p for p in u.parents
                    if (p.verify_key not in info) or (p.height > info[p.verify_key])]

        subset = [h
                  for h in bfs((self.head,), succ)]
        return subset

    def ancestors(self, c):
        while True:
            yield c
            if not c.parents:
                return
            c = c.parents[0]

    def maxi(self, a, b):
        if self.higher(a, b):
            return a
        else:
            return b

    def _higher(self, a, b):
        for x, y in zip_longest(self.ancestors(a), self.ancestors(b)):
            if x == b or y is None:
                return True
            elif y == a or x is None:
                return False

    def higher(self, a, b):
        return a is not None and (b is None or a.height >= b.height)

    def divide_rounds(self, events):
        """Restore invariants for `can_see`, `witnesses` and `round`.

        :param events: topologicaly sorted sequence of new event to process.
        """

        for h in events:
            ev = h
            if ev.parents == ():  # this is a root event
                h.round = 0
                self.witnesses[0][ev.verify_key] = h
                h.can_see = {ev.verify_key: h}
            else:
                r = max(p.round for p in ev.parents)

                # recurrence relation to update can_see
                p0, p1 = (p.can_see for p in ev.parents)
                h.can_see = {c: self.maxi(p0.get(c), p1.get(c))
                             for c in p0.keys() | p1.keys()}

                # count distinct paths to distinct nodes
                hits = defaultdict(int)
                for c, k in h.can_see.items():
                    if k.round == r:
                        for c_, k_ in k.can_see.items():
                            if k_.round == r:
                                hits[c_] += self.stake[c]
                # check if i can strongly see enough events
                if sum(1 for x in hits.values() if x > self.min_s) > self.min_s:
                    h.round = r + 1
                else:
                    h.round = r
                h.can_see[ev.verify_key] = h
                if h.round > ev.parents[0].round:
                    self.witnesses[h.round][ev.verify_key] = h

    def decide_fame(self):
        max_r = max(self.witnesses)
        max_c = 0
        while max_c in self.consensus:
            max_c += 1

        # helpers to keep code clean
        def iter_undetermined(r_):
            for r in range(max_c, r_):
                if r not in self.consensus:
                    for w in self.witnesses[r].values():
                        if w not in self.famous:
                            yield r, w

        def iter_voters():
            for r_ in range(max_c + 1, max_r + 1):
                for w in self.witnesses[r_].values():
                    yield r_, w

        done = set()

        for r_, y in iter_voters():  # type: int, Event

            hits = defaultdict(int)
            for c, k in y.can_see.items():
                if k.round == r_ - 1:
                    for c_, k_ in k.can_see.items():
                        if k_.round == r_ - 1:
                            hits[c_] += self.stake[c]
            s = {self.witnesses[r_ - 1][c] for c, n in hits.items()
                 if n > self.min_s}

            for r, x in iter_undetermined(r_):
                if r_ - r == 1:
                    y.votes[x] = x in s
                else:
                    filtered_s = filter(lambda w: w in self.lookup_table, s)  # TODO: check why filtering is necessary
                    v, t = majority((self.stake[self.lookup_table[w].verify_key], w.votes[x]) for w in filtered_s)
                    if (r_ - r) % C != 0:
                        if t > self.min_s:
                            self.famous[x] = v
                            done.add(r)
                        else:
                            y.votes[x] = v
                    else:
                        if t > self.min_s:
                            y.votes[x] = v
                        else:
                            # the 1st bit is same as any other bit right? # TODO not!
                            y.votes[x] = bool(y.signature[0] // 128)

        new_c = {r for r in done
                 if all(w in self.famous for w in self.witnesses[r].values())}
        self.consensus |= new_c
        return new_c

    def find_order(self, new_c):
        def to_int(x):
            return int.from_bytes(self.lookup_table[x].signature, byteorder='big')

        for r in sorted(new_c):
            f_w = {w for w in self.witnesses[r].values() if self.famous[w]}
            white = reduce(lambda a, b: a ^ to_int(b), f_w, 0)
            ts = {}
            seen = set()
            for x in bfs(filter(self.tbd.__contains__, f_w),
                         lambda u: (p for p in self.lookup_table[u].parents if p in self.tbd)):
                c = self.lookup_table[x].verify_key
                s = {w for w in f_w if c in w.can_see
                     and self.higher(w.can_see[c], x)}
                if sum(self.stake[self.lookup_table[w].verify_key] for w in s) > self.tot_stake / 2:
                    self.tbd.remove(x)
                    seen.add(x)
                    times = []
                    for w in s:
                        a = w
                        while (c in a.can_see
                               and self.higher(a.can_see[c], x)
                               and self.lookup_table[a].parents):
                            a = self.lookup_table[a].p[0]
                        times.append(self.lookup_table[a].t)
                    times.sort()
                    ts[x] = .5 * (times[len(times) // 2] + times[(len(times) + 1) // 2])
            final = sorted(seen, key=lambda x: (ts[x], white ^ to_int(x)))
            for i, x in enumerate(final):
                self.idx[x] = i + len(self.transactions)
            self.transactions += final
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
