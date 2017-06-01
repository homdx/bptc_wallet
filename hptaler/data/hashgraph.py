from collections import defaultdict
from functools import reduce

from hptaler.data.event import Event, Parents
from hptaler.data.member import Member

from utilities.utils import bfs
from utilities.log_helper import logger

C = 6  # How often a coin round occurs, e.g. 6 for every sixth round


class Hashgraph:
    """
    The Hashgraph - storing the events of all nodes
    """

    def __init__(self, me):
        # Member: A reference to the current user. For convenience (e.g. signing)
        self.me: Member = me

        # int: The total stake in the hashgraph
        self.total_stake = None

        # int: The stake needed for a supermajority (2/3 of total)
        self.supermajority_stake = None

        # {event-hash => event}: Dictionary mapping hashes to events
        self.lookup_table = {}

        # {event-hash}: Events for which the final order has not yet been determined
        self.unordered_events = set()

        # [event-hash]: Final order of events
        self.ordered_events = []

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

    def get_head_of(self, member: Member):
        """
        Returns the head of a given member
        :param member:
        :return:
        """
        height = -1
        head = None
        for item_id, item in self.lookup_table.items():
            if str(item.verify_key) == str(member):
                if item.height > height:
                    head = item
                    height = item.height
        return head

    def add_own_first_event(self, event: Event):
        """
        Adds the own initial event to the hashgraph
        :param event: The event to be added
        :return: void
        """
        # Add the event
        self.add_own_event(event)

        # Make the new event a witness for round 0
        self.witnesses[0][event.creator_verify_key] = event

    def add_own_event(self, event: Event):
        """
        Adds an own event to the hashgraph, setting the event's height depending on its parents
        :param event: The event to be added
        :return: void
        """

        # Set the event's correct height
        if event.parents.self_parent is not None:
            self_parent_height = self.lookup_table[event.parents.self_parent].height
        else:
            self_parent_height = -1
        if event.parents.other_parent is not None:
            other_parent_height = self.lookup_table[event.parents.other_parent].height
        else:
            other_parent_height = -1
        event.height = max(self_parent_height, other_parent_height) + 1

        # Sign event body
        event.signature = self.me.signing_key.sign(event.body).signature

        self.lookup_table[event.id] = event

        # Update cached head
        self.me.head = event

        logger.info("Added event to hashgraph: " + str(event))

    # TODO: move to User
    def set_stake(self, stake):
        self.stake = stake
        self.total_stake = sum(stake.values())
        self.supermajority_stake = 2 * self.total_stake / 3  # min stake amount

    def is_valid_event(self, id, event: Event):
        """
        Checks whether an event is valid (signature valid, parents known)
        :param id: The event's ID
        :param event: The event to be checked
        :return: boolean: Whether the event is valid
        """
        # Verify signature is valid
        try:
            event.creator_verify_key.verify(event.body, event.signature)
        except ValueError:
            return False

        # Verify parents exist
        return (event.id == id
                and (event.parents == ()
                     or (len(event.parents) == 2
                         and event.parents[0].id in self.lookup_table and event.parents[1].id in self.lookup_table
                         and event.parents[0].creator_verify_key == event.creator_verify_key
                         and event.parents[1].creator_verify_key != event.creator_verify_key)))

        # TODO: check if there is a fork (rly need reverse edges?)
        # and all(x.verify_key != ev.verify_key
        #        for x in self.preds[ev.parents[0]]))))

    @staticmethod
    def get_fingerprint(member: Member):
        """Returns dict of heights for each member."""
        return {}

    def keys(self):
        return self.lookup_table.keys()

    def difference(self, info):
        """Difference with given hashgraph info (fingerprint?)"""

        # NOTE we need bfs() due to cheating possibility -- several children of one parent
        # succ = lambda u: (p for p in u.parents
        #                if (p.verify_key not in info) or (p.height > info[p.verify_key]))
        def succ(u):
            return [p for p in u.parents
                    if (p.creator_verify_key not in info) or (p.height > info[p.verify_key])]

        subset = [h for h in bfs((self.head,), succ)]
        return subset

    @staticmethod
    def ancestors(event: Event):
        """
        A Generator returning the ancesors of a given event
        :param event: The event
        :return: A Generator for the event's parents
        """
        while True:
            yield event
            if not event.parents:
                return
            event = event.parents[0]

    @staticmethod
    def get_higher(a: Event, b: Event):
        """
        Returns the higher of two given events
        :param a: The first event
        :param b: The second event
        :return: Event: The higher event: a or b
        """
        if Hashgraph.is_higher(a, b):
            return a
        else:
            return b

    @staticmethod
    def is_higher(a: Event, b: Event):
        """
        Checks whether one event is higher than another event
        :param a: The event to be checked
        :param b: The event to be checked against
        :return: boolean: Whether a is higher than b
        """
        return a is not None and (b is None or a.height >= b.height)

    def divide_rounds(self, events):
        """Restore invariants for `can_see`, `witnesses` and `round`.

        :param events: Topologicaly sorted sequence of new event to process.
        """

        for event in events:
            # Check if this is a root event or not
            if event.parents == ():
                # This is a root event
                event.round = 0
                self.witnesses[0][event.creator_verify_key] = event
                event.can_see = {event.creator_verify_key: event}
            else:
                # This is a normal event
                # Estimate round (= maximum round of parents)
                calculated_round = max(parent.round for parent in event.parents)

                # recurrence relation to update can_see
                # TODO: What exactly happens here?
                p0, p1 = (p.can_see for p in event.parents)
                event.can_see = {c: self.get_higher(p0.get(c), p1.get(c))
                             for c in p0.keys() | p1.keys()}

                # Count distinct paths to distinct nodes
                # TODO: What exactly happens here? Why two levels of visible events?
                hits = defaultdict(int)
                for creator_verify_key, visible_event in event.can_see.items():
                    if visible_event.round == calculated_round:
                        for c_, k_ in visible_event.can_see.items():
                            if k_.round == calculated_round:
                                hits[c_] += self.stake[creator_verify_key]

                # check if i can strongly see enough events
                if sum(1 for x in hits.values() if x > self.supermajority_stake) > self.supermajority_stake:
                    event.round = calculated_round + 1
                else:
                    event.round = calculated_round

                # Events can always see themselves
                event.can_see[event.creator_verify_key] = event

                # An event becomes a witness if it is the first of that round
                if event.round > event.parents[0].round:
                    self.witnesses[event.round][event.creator_verify_key] = event

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

        def iterate_witnesses():
            """
            A Generator for all witnesses that need to be handled
            :return: A Generator for all witnesses that need to be handled
            """
            # For every round that has to be handled ...
            for round in range(max_c + 1, max_r + 1):
                # ... iterate over the witnesses of that round ...
                for witness in self.witnesses[round].values():
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
                            hits[c_] += self.stake[c]
            s = {self.witnesses[round - 1][c] for c, n in hits.items()
                 if n > self.supermajority_stake}

            for r, x in iter_undetermined(round):
                if round - r == 1:
                    witness.votes[x] = x in s
                else:
                    filtered_s = filter(lambda w: w in self.lookup_table, s)  # TODO: check why filtering is necessary
                    v, t = majority((self.stake[self.lookup_table[w].creator_verify_key], w.votes[x]) for w in filtered_s)
                    if (round - r) % C != 0:
                        if t > self.supermajority_stake:
                            self.famous[x] = v
                            done.add(r)
                        else:
                            witness.votes[x] = v
                    else:
                        if t > self.supermajority_stake:
                            witness.votes[x] = v
                        else:
                            # the 1st bit is same as any other bit right? # TODO not!
                            witness.votes[x] = bool(witness.signature[0] // 128)

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
            for x in bfs(filter(self.unordered_events.__contains__, f_w),
                         lambda u: (p for p in self.lookup_table[u].parents if p in self.unordered_events)):
                c = self.lookup_table[x].creator_verify_key
                s = {w for w in f_w if c in w.can_see
                     and self.is_higher(w.can_see[c], x)}
                if sum(self.stake[self.lookup_table[w].creator_verify_key] for w in s) > self.total_stake / 2:
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

    def process_events(self, from_member: Member, events):
        """
        Processes a list of events
        :param from_member: The member from whom the events were received
        :param events: The events to be processed
        :return: void
        """
        # Add all new events
        for event_id, event in events.items():
            if event_id not in self.lookup_table:
                self.lookup_table[event_id] = event

        # Create a new event for the gossip
        event = Event(self.me.verify_key, None, Parents(self.me.head.id, self.get_head_of(from_member).id))
        self.add_own_event(event)


def majority(it):
    hits = [0, 0]
    for s, x in it:
        hits[int(x)] += s
    if hits[0] > hits[1]:
        return False, hits[0]
    else:
        return True, hits[1]
