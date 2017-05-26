from random import choice
from twisted.internet import threads, reactor
from hashgraph.event import Parents
from hashgraph.hashgraph import Hashgraph
from networking.push_protocol import *
from utilities.signing import SigningKey


class Member:

    def __init__(self, signing_key):
        self.signing_key = signing_key  # TODO implement

        self.neighbours = {}  # dict(pk -> Member)
        self.hashgraph = Hashgraph()

        # init first local event
        self.head = None
        event = self.create_first_event()
        self.hashgraph.add_first_event(event)
        self.head = event

    @classmethod
    def create(cls):
        """Creates new member.
        Generate singing and verification keys. ID will be as verification key."""
        signing_key = SigningKey.generate()
        return cls(signing_key)

    def set(self, stake):
        self.hashgraph.set_stake(stake)

    def acquaint(self, member):
        """- acquaint with Member"""
        self.neighbours[member.id] = member

    def forget(self, member):
        """Forget neighbour member."""
        del self.neighbours[member.id]

    @property
    def id(self):
        return self.signing_key.verify_key

    def __str__(self):
        return "Member({})".format(self.id)

    def received_data_callback(self, events):
            self.process_received_events(events)

    def push_to(self, ip, port):
        """Update hg and return new event ids in topological order."""
        fingerprint = self.hashgraph.get_fingerprint(self)

        factory = PushClientFactory(self.hashgraph.lookup_table)

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

    def process_received_events(self, events):
        for event_id, event in events.items():
            if event_id not in self.hashgraph.lookup_table:
                self.hashgraph.lookup_table[event_id] = event

    def heartbeat(self):
        event = self._new_event(None, Parents(self.head.id, None))
        self.hashgraph.add_event(self.head, event)
        self.head = event
        return event

    def create_first_event(self):
        event = self._new_event(None, Parents(None, None))
        event.round = 0
        event.can_see = {event.verify_key: event}
        return event

    def _new_event(self, data, parents_id):
        # TODO: fail if an ancestor of p[1] from creator self.pk is not an ancestor of p[0] ???
        event = Event(self.signing_key.verify_key, data, parents_id)
        # set event height
        if parents_id.self_parent is not None:
            self_parent_height = self.hashgraph.lookup_table[parents_id.self_parent].height
        else:
            self_parent_height = -1
        if parents_id.other_parent is not None:
            other_parent_height = self.hashgraph.lookup_table[parents_id.other_parent].height
        else:
            other_parent_height = -1
        event.height = max(self_parent_height, other_parent_height) + 1
        # sign event body
        event.signature = self.signing_key.sign(event.body).signature
        logger.info("{} created new event {}".format(self, event))
        return event

    # TODO: remove
    def ask_sync(self, member, fingerprint):
        """Respond to someone wanting to sync (only public method)."""

        # TODO: only send a diff? maybe with the help of self.height
        # TODO: thread safe? (allow to run while mainloop is running)

        subset = self.hashgraph.difference(fingerprint)

        # TODO Clear response from internal information !!!

        return self.hashgraph.head, subset

    # TODO: remove
    def heartbeat_callback(self):
        """Main working loop."""

        logger.info("{} heartbeat...".format(self))

        # payload = [event.id for event in self.new]
        payload = ()
        self.new = []

        logger.debug("{}.payload = {}".format(self, payload))

        # pick a random member to sync with but not me
        if len(list(self.neighbours.values())) == 0:
            logger.error("No known neighbours!")
            return None

        member = choice(list(self.neighbours.values()))
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
