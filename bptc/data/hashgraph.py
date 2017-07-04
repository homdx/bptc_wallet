import math
import threading
from collections import defaultdict
from typing import Dict
import bptc
from bptc.data.consensus import divide_rounds, decide_fame, find_order
from bptc.data.event import Event, Parents
from bptc.data.member import Member
from bptc.utils.toposort import toposort
from bptc.data.transaction import MoneyTransaction, TransactionStatus, PublishNameTransaction


class Hashgraph:
    """
    The Hashgraph - storing the events of all nodes
    """

    def __init__(self, me):
        self.lock = threading.Lock()
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
        self.next_ordered_event_idx_to_process = 0

        self.idx = {}

        # {round-num}: rounds where fame is fully decided
        self.rounds_with_decided_fame = set()

        # {round-num => {member-pk => event-hash}}:
        self.witnesses = defaultdict(dict)

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

    def get_unknown_events_of(self, member: Member) -> Dict[str, Event]:
        """
        Returns the presumably unknown events of a given member, in the same format as lookup_table
        :param member: The member for which to return unknown events
        :return: Dictionary mapping hashes to events
        """
        result = dict(self.lookup_table)
        head = member.head

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

    def add_own_event(self, event: Event):
        """
        Adds an own event to the hashgraph, setting the event's height depending on its parents
        :param event: The event to be added
        :param first: whether it is the first event
        :return: None
        """

        # Sign event body
        event.sign(self.me.signing_key)

        # Add event
        self.add_event(event)

        # Figure out rounds, fame, etc.
        divide_rounds(self, [event])
        decide_fame(self)
        find_order(self)
        self.process_ordered_events()

    def add_event(self, event: Event):
        # Set the event's correct height
        if event.parents.self_parent:
            event.height = self.lookup_table[event.parents.self_parent].height + 1

        # Add event to graph
        self.lookup_table[event.id] = event

        # Update caches
        self.unordered_events.add(event.id)
        if self.known_members[event.verify_key].head is None or \
                event.height > self.lookup_table[self.known_members[event.verify_key].head].height:
            self.known_members[event.verify_key].head = event.id

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
        events_toposorted = toposort(events)

        # Learn about other members
        self.learn_members_from_events(events)

        # Add all new events in topological order and check parent pointer
        new_events = {}
        for event in events_toposorted:
            if event.id not in self.lookup_table:
                if event.parents.self_parent is not None and event.parents.self_parent not in self.lookup_table:
                    raise AssertionError('Self parent {} of {} not known'.
                                         format(event.parents.self_parent[:6], event.id[:6]))
                if event.parents.other_parent is not None and event.parents.other_parent not in self.lookup_table:
                    raise AssertionError('Other parent {} of {} not known'.
                                         format(event.parents.other_parent[:6], event.id[:6]))
                new_events[event.id] = event
                self.add_event(event)

        # Create a new event for the gossip
        event = Event(self.me.verify_key, None, Parents(self.me.head, from_member.head))
        self.add_own_event(event)
        new_events[event.id] = event

        # Figure out fame, order, etc.
        divide_rounds(self, toposort(new_events))
        decide_fame(self)
        find_order(self)
        self.process_ordered_events()

    def learn_members_from_events(self, events: Dict[str, Event]) -> None:
        """
        Goes through a list of events and learns their creators if they are not already known
        :param events: The list of events
        :return: None
        """
        for event in events.values():
            if event.verify_key not in self.known_members:
                self.known_members[event.verify_key] = Member(event.verify_key, None)

    def process_ordered_events(self):
        for event_id in self.ordered_events[self.next_ordered_event_idx_to_process:len(self.ordered_events)]:
            event = self.lookup_table[event_id]
            if event.data is None:
                continue

            for transaction in event.data:
                sender = self.known_members[event.verify_key]
                if isinstance(transaction, MoneyTransaction):
                    receiver = self.known_members[transaction.receiver]

                    # Check if the sender has the funds
                    if sender.account_balance < transaction.amount:
                        transaction.status = TransactionStatus.DENIED
                    else:
                        sender.account_balance -= transaction.amount
                        receiver.account_balance += transaction.amount
                        transaction.status = TransactionStatus.CONFIRMED
                elif isinstance(transaction, PublishNameTransaction):
                    sender.name = transaction.name

        self.next_ordered_event_idx_to_process = len(self.ordered_events)


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
