from random import choice
from typing import Dict, List
from twisted.internet import threads, reactor
from bptc.data.event import Event, Parents
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member
from bptc.data.transaction import MoneyTransaction
from bptc.networking.push_protocol import PushClientFactory
from bptc.utils import logger
from bptc.data.utils import filter_members_with_address


class Network:
    """
    An abstraction of the P2P network
    This should be the main API of the
    """

    def __init__(self, hashgraph: Hashgraph, create_initial_event: bool = True):
        # The current hashgraph
        self.hashgraph = hashgraph
        self.me = self.hashgraph.me

        # Create first own event
        if create_initial_event:
            self.create_own_first_event()

    def push_to(self, ip, port) -> None:
        """Update hg and return new event ids in topological order."""
        fingerprint = self.hashgraph.get_fingerprint(self)

        factory = PushClientFactory(self.hashgraph.me,
                                    self.hashgraph.lookup_table,
                                    filter_members_with_address(self.hashgraph.known_members.values()))

        def push():
            reactor.connectTCP(ip, port, factory)

        threads.blockingCallFromThread(reactor, push)

        # NOTE: communication channel security must be provided in standard way: SSL

        # remote_head, difference = member.ask_sync(self, fingerprint)
        # logger.info("  remote_head = {}".format(remote_head))
        # logger.info("  difference  = {}".format(difference))
        #
        # # TODO move to hashgraph
        # new = tuple(toposort([event for event in difference if event.id not in self.hashgraph.lookup_table],
        #                      # difference.keys() - self.hashgraph.keys(),
        #                      lambda u: u.parents))
        #
        # logger.info("{}.sync:new = \n{}".format(self, pformat(new)))
        #
        # # TODO move to hashgraph
        # for event in new:
        #     if self.hashgraph.is_valid_event(event.id, event):  # TODO check?
        #         self.hashgraph.add_event(event)  # (, h) ??
        #
        # # TODO move to hashgraph
        # # TODO check DOUBLE add remote_head ?
        # if self.hashgraph.is_valid_event(remote_head.id, remote_head):  # TODO move id check to communication part
        #     event = self.hashgraph.new_event(payload, remote_head, self.signing_key)
        #     self.hashgraph.add_event(event)
        #     self.hashgraph.head = event
        #     h = event.id
        #
        # logger.info("{}.sync exits.".format(self))
        #
        # return new + (event,)
        return

    def push_to_member(self, member: Member) -> None:
        logger.info('Push to {}... ({}, {})'.format(member.verify_key[:6], member.address.host, member.address.port))
        self.push_to(member.address.host, member.address.port)

    def push_to_random(self) -> None:
        """
        Pushes to a random, known member
        :return: None
        """
        if self.hashgraph.known_members:
            member_id, member = choice(list(self.hashgraph.known_members.items()))
            # Don't send messages to ourselves
            while member_id == self.me.id:
                member_id, member = choice(list(self.hashgraph.known_members.items()))
            self.push_to_member(member)
        else:
            logger.info("Don't know any other members. Get them from the registry!")  # one self is always in known_members, right?

    def heartbeat(self) -> Event:
        """
        Creates a heartbeat (= own, empty) event and adds it to the hashgraph
        :return: The newly created event
        """
        # TODO: Remove test transaction
        event = Event(self.hashgraph.me.verify_key, [MoneyTransaction(self.me.to_verifykey_string(), 1)],
                      Parents(self.hashgraph.me.head, None))
        self.hashgraph.add_own_event(event)
        return event

    def create_own_first_event(self) -> Event:
        """
        Creates the own initial event and adds it to the hashgraph
        :return: The newly created event
        """
        event = Event(self.hashgraph.me.verify_key, None, Parents(None, None))
        event.round = 0
        event.can_see = {event.verify_key: event}
        self.hashgraph.add_own_first_event(event)
        return event

    def receive_events_callback(self, from_member: Member, events: Dict[str, Event]) -> None:
        """
        Used as a callback when events are received from the outside
        :param from_member: The member from which the events were received
        :param events: The list of events
        :return: None
        """
        # Store/Update member
        if from_member in self.hashgraph.known_members:
            self.hashgraph.known_members[from_member.id].address = from_member.address
        else:
            self.hashgraph.known_members[from_member.id] = from_member

        # Let the hashgraph process the events
        self.hashgraph.process_events(from_member, events)

    def receive_members_callback(self, members: List[Member]) -> None:
        """
        Used as a callback when member are received from the outside
        :param members: The ist of members
        :return: None
        """
        for member in members:
            if member.id not in self.hashgraph.known_members:
                self.hashgraph.known_members[member.id] = member
            elif self.hashgraph.known_members[member.id].address is None:
                self.hashgraph.known_members[member.id].address = member.address
