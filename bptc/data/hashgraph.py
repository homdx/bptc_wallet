import math
from collections import defaultdict
from functools import reduce
from typing import List, Dict

from libnacl.encode import base64_decode

from bptc.data.event import Event, Parents
from bptc.data.member import Member
from bptc.utils import bfs
from bptc.utils import logger

C = 6  # How often a coin round occurs, e.g. 6 for every sixth round


class Hashgraph:
    """
    The Hashgraph - storing the events of all nodes
    """

    def __init__(self, me):
        # Member: A reference to the current user. For convenience (e.g. signing)
        self.me = me

        # {member-id => Member}: All members we know
        if me is not None:
            self.known_members = {me.id: me}

        # {event-hash => event}: Dictionary mapping hashes to events
        self.lookup_table = {}

        # {event-hash}: Events for which the final order has not yet been determined
        self.unordered_events = set()

        # [event-hash]: Final order of events
        self.ordered_events = []

        self.idx = {}

        # {round-num}: rounds where fame is fully decided
        self.consensus = set()

        # {round-num => {member-pk => event-hash}}:
        self.witnesses = defaultdict(dict)

        self.famous = {}

    @property
    def total_stake(self) -> int:
        """
        :return: The total stake in the hashgraph
        """
        return sum([member.stake for _, member in self.known_members.items()])

    @property
    def supermajority_stake(self) -> int:
        """
        :return: The stake needed for a supermajority (2/3 of total)
        """
        return int(math.floor(2 * self.total_stake / 3))

    def get_head_of(self, member: Member) -> str:
        """
        Returns the id of the head of a given member
        :param member:
        :return:
        """
        height = -1
        head = None
        for item_id, item in self.lookup_table.items():
            if str(item.verify_key) == str(member.verify_key):
                if item.height > height:
                    head = item
                    height = item.height
        return head.id

    def add_own_first_event(self, event: Event):
        """
        Adds the own initial event to the hashgraph
        :param event: The event to be added
        :return: None
        """
        # Add the event
        self.add_own_event(event)

        # Make the new event a witness for round 0
        self.witnesses[0][event.verify_key] = event

    def add_own_event(self, event: Event):
        """
        Adds an own event to the hashgraph, setting the event's height depending on its parents
        :param event: The event to be added
        :return: None
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
        event.sign(self.me.signing_key)

        # Add event to graph
        self.lookup_table[event.id] = event

        # Update cached head
        self.me.head = event.id

        # Figure out rounds, fame, etc.
        self.divide_rounds([event])
        new_c = self.decide_fame()
        self.find_order(new_c)

        #logger.info("Added own event to hashgraph: " + str(event))

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
                    if (p.verify_key not in info) or (p.height > info[p.verify_key])]

        subset = [h for h in bfs((self.lookup_table[self.head],), succ)]
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

        #logger.info("Dividing rounds for {} events".format(len(events)))

        for event in events:
            # Check if this is a root event or not
            if event.parents == () or (event.parents.self_parent is None and event.parents.other_parent is None):
                # This is a root event
                event.round = 0
                self.witnesses[0][event.verify_key] = event
                event.can_see = {event.verify_key: event}
            else:
                # This is a normal event
                # Estimate round (= maximum round of parents)
                #logger.info("Checking {}".format(str(event.parents)))
                calculated_round = 0
                for parent in event.parents:
                    if parent is not None and self.lookup_table[parent].round > calculated_round:
                        calculated_round = self.lookup_table[parent].round

                # recurrence relation to update can_see
                p0 = self.lookup_table[event.parents.self_parent].can_see if event.parents.self_parent is not None else dict()
                p1 = self.lookup_table[event.parents.other_parent].can_see if event.parents.other_parent is not None else dict()
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
                            hits[c_] += self.known_members[c].stake
            s = {self.witnesses[round - 1][c] for c, n in hits.items()
                 if n > self.supermajority_stake}

            for r, x in iter_undetermined(round):
                if round - r == 1:
                    witness.votes[x] = x in s
                else:
                    filtered_s = filter(lambda w: w in self.lookup_table, s)  # TODO: check why filtering is necessary
                    v, t = majority((self.known_members[self.lookup_table[w].verify_key].stake, w.votes[x]) for w in filtered_s)
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
                            witness_signature_byte = base64_decode(witness.signature.encode("UTF-8"))
                            witness.votes[x] = bool(witness_signature_byte[0] // 128)

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

    def process_events(self, from_member: Member, events: Dict[str, Event]) -> None:
        """
        Processes a list of events
        :param from_member: The member from whom the events were received
        :param events: The events to be processed
        :return: None
        """
        logger.info("Processing {} events from {}...".format(len(events), from_member.verify_key[:6]))

        # Only deal with valid events
        events = filter_valid_events(events)

        # Add all new events
        new_events = []
        for event_id, event in events.items():
            if event_id not in self.lookup_table:
                new_events.append(event)
                self.lookup_table[event_id] = event

        # Learn about other members
        self.learn_members_from_events(new_events)

        # Figure out fame, order, etc.
        self.divide_rounds(new_events)
        new_c = self.decide_fame()
        self.find_order(new_c)

        # Create a new event for the gossip
        event = Event(self.me.verify_key, None, Parents(self.me.head, self.get_head_of(from_member)))
        self.add_own_event(event)

    def add_events(self, events: Dict[str, Event]) -> None:
        """
        Adds a list of events to the hashgraph
        :param events: The events to be added
        :return: None
        """
        logger.info("Adding {} events".format(len(events)))

        # Only deal with valid events
        events = filter_valid_events(events)
        logger.info("{} events are valid".format(len(events)))

        # Add all new events
        new_events = []
        for event_id, event in events.items():
            if event_id not in self.lookup_table:
                new_events.append(event)
                self.unordered_events.add(event)
                self.lookup_table[event_id] = event

        # Learn about other members
        self.learn_members_from_events(new_events)

        # Figure out fame, order, etc.
        self.divide_rounds(new_events)
        new_c = self.decide_fame()
        self.find_order(new_c)

    def learn_members_from_events(self, events: List[Event]) -> None:
        """
        Goes through a list of events and learns their creators if they are not already known
        :param events: The list of events
        :return: None
        """
        for event in events:
            if event.verify_key not in self.known_members:
                self.known_members[event.verify_key] = Member(event.verify_key)


def majority(it):
    hits = [0, 0]
    for s, x in it:
        hits[int(x)] += s
    if hits[0] > hits[1]:
        return False, hits[0]
    else:
        return True, hits[1]


def filter_valid_events(events: Dict[str, Event]) -> Dict[str, Event]:
    """
    Goes through a dict of events and returns a dict containing only the valid ones
    :param events: The dict to be filtered
    :return: A dict containing only valid events
    """
    result = dict()
    for event_id, event in events.items():
        if event.has_valid_signature:
            result[event_id] = event
        else:
            logger.warn("Event had invalid signature: {}".format(event))

    return result