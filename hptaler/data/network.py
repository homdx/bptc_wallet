from hptaler.data.member import Member
from hptaler.data.hashgraph import Hashgraph
from hptaler.data.event import Event, Parents

from twisted.internet import threads, reactor
from networking.push_protocol import PushClientFactory

from utilities.log_helper import logger

from random import choice

from typing import List


class Network:
    """
    An abstraction of the P2P network
    This should be the main API of the
    """

    def __init__(self, hashgraph: Hashgraph):
        # The current hashgraph
        self.hashgraph = hashgraph
        self.me = self.hashgraph.me

        # Create first own event
        self.create_own_first_event()

    def push_to(self, ip, port) -> None:
        """Update hg and return new event ids in topological order."""
        fingerprint = self.hashgraph.get_fingerprint(self)

        factory = PushClientFactory(self.hashgraph.me, self.hashgraph.lookup_table)

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
            logger.info("Don't know any other members. Get them from the registry!")

    def heartbeat(self) -> Event:
        """
        Creates a heartbeat (= own, empty) event and adds it to the hashgraph
        :return: The newly created event
        """
        event = Event(self.hashgraph.me.verify_key, None, Parents(self.hashgraph.me.head.id, None))
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

    def receive_events_callback(self, from_member: Member, events: List[Event]) -> None:
        """
        Used as a callback when events are received from the outside
        :param from_member: The member from which the events were received
        :param events: The list of events
        :return:
        """
        # Store/Update member
        self.hashgraph.known_members[from_member.id] = from_member

        # Let the hashgraph process the events
        self.hashgraph.process_events(from_member, events)


    # TODO: remove
    def ask_sync(self, member, fingerprint):
        """Respond to someone wanting to sync"""

        # TODO: only send a diff? maybe with the help of self.height
        # TODO: thread safe? (allow to run while mainloop is running)

        subset = self.hashgraph.difference(fingerprint)

        # TODO Clear response from internal information !!!

        return self.hashgraph.me.head, subset

    # TODO: remove
    def heartbeat_callback(self):
        """Main working loop."""

        logger.info("{} heartbeat...".format(self))

        # payload = [event.id for event in self.new]
        payload = ()
        self.new = []

        logger.debug("{}.payload = {}".format(self, payload))

        # pick a random member to sync with but not me
        if len(list(self.hashgraph.known_members.values())) == 0:
            logger.error("No known neighbours!")
            return None

        member = choice(list(self.hashgraph.known_members.values()))
        logger.info("{}.sync with {}".format(self, member))
        new = self.push_to(member, payload)

        logger.info("{}.new = {}".format(self, new))

        self.new = list(new)

        self.hashgraph.divide_rounds(new)

        new_c = self.hashgraph.decide_fame()
        self.hashgraph.find_order(new_c)

        logger.info("{}.new_c = {}".format(self, new_c))
        logger.info("{}.heartbeat exits.".format(self))

        # return payload
        return self.new
