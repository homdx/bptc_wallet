import math
from collections import defaultdict
from functools import partial
from typing import Dict
import bptc
from bptc.data import consensus, consensus_new
from bptc.data.event import Event, Parents
from bptc.data.member import Member
from bptc.data.utils import bfs
from bptc.utils.toposort import toposort


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
        self.rounds_with_decided_fame = set()

        # {round-num => {member-pk => event-hash}}:
        self.witnesses = defaultdict(dict)

        # add functions of hashgraph algorithm
        self.divide_rounds = partial(consensus_new.divide_rounds, self)
        self.decide_fame = partial(consensus_new.decide_fame, self)
        self.find_order = partial(consensus.find_order, self)

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
        return head.id if head is not None else None

    def get_unknown_events_of(self, member: Member) -> Dict[str, Event]:
        """
        Returns the presumably unknown events of a given member, in the same format as lookup_table
        :param member: The member for which to return unknown events
        :return: Dictionary mapping hashes to events
        """
        result = dict(self.lookup_table)
        head = self.get_head_of(member)

        if head is None:
            return result

        to_visit = {head}
        visited = set()

        while len(to_visit) > 0:
            event_id = to_visit.pop()
            if event_id not in visited:
                event = result[event_id]
                del result[event_id]
                if event.parents.self_parent is not None:
                    to_visit.add(event.parents.self_parent)
                if event.parents.other_parent is not None:
                    to_visit.add(event.parents.other_parent)
                visited.add(event_id)

        return result

    def add_own_first_event(self, event: Event):
        """
        Adds the own initial event to the hashgraph
        :param event: The event to be added
        :return: None
        """
        # Add the event
        self.add_own_event(event)

        # Make the new event a witness for round 0
        self.witnesses[0][event.verify_key] = event.id

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
        self.decide_fame()
        #self.find_order(new_c)

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
        A Generator returning the ancestors of a given event
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

    def process_events(self, from_member: Member, events: Dict[str, Event]) -> None:
        """
        Processes a list of events
        :param from_member: The member from whom the events were received
        :param events: The events to be processed
        :return: None
        """
        bptc.logger.info("Processing {} events from {}...".format(len(events), from_member.verify_key[:6]))

        # Only deal with valid events
        events = filter_valid_events(events)

        # Add all new events
        new_events = {}
        for event_id, event in events.items():
            if event_id not in self.lookup_table:
                new_events[event.id] = event
                self.lookup_table[event_id] = event

        # Learn about other members
        self.learn_members_from_events(new_events)

        # Create a new event for the gossip
        event = Event(self.me.verify_key, None, Parents(self.me.head, self.get_head_of(from_member)))
        self.add_own_event(event)
        new_events[event.id] = event

        # Figure out fame, order, etc.
        self.divide_rounds(toposort(self, new_events))
        self.decide_fame()
        #self.find_order(new_c)

    def learn_members_from_events(self, events: Dict[str, Event]) -> None:
        """
        Goes through a list of events and learns their creators if they are not already known
        :param events: The list of events
        :return: None
        """
        for event in events.values():
            if event.verify_key not in self.known_members:
                self.known_members[event.verify_key] = Member(event.verify_key)


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
            bptc.logger.warn("Event had invalid signature: {}".format(event))

    return result


def init_hashgraph(app):
    from bptc.data.db import DB
    from bptc.data.network import Network

    # Try to load the Hashgraph from the database
    app.hashgraph = DB.load_hashgraph(
        app.cl_args.port, app.cl_args.output)
    # Create a new hashgraph if it could not be loaded
    if app.hashgraph is None or app.hashgraph.me is None:
        app.me = Member.create()
        app.hashgraph = Hashgraph(app.me)
        app.network = Network(app.hashgraph, create_initial_event=True)
    else:
        app.network = Network(app.hashgraph, create_initial_event=False)
        app.me = app.hashgraph.me
