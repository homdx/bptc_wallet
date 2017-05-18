from hashgraph import Hashgraph
from sklavit_nacl.signing import *
import logging
from random import choice
from utils import toposort
from pprint import pformat


class Node:
    """A node in a hashgraph network.

    Note can:
    - process incoming requests.
    - generate requests

    Node <==> Node <==> User

    Network == set of working Nodes

    Node -- User:
    - create
    - dump/load identity
    - start (and connect to network), ready to process requests
    - shutdown
    -----
    - acquaint with Node
    - forget Node
    -----
    - get (full) state; get consensus as sub-request
    - send message
    - subscribe / unsubscribe listener
    -----

    Node -- Node:
    - ping ?; return ping time
    - get( what to get ?); returns response
    - post(message); returns response
    - pinged_get
    - pinged_post


    """

    def __init__(self, signing_key):
        self.signing_key = signing_key  # TODO implement

        self.neighbours = {}  # dict(pk -> Node)

        self.hashgraph = Hashgraph()

        # init first local event
        event = self.hashgraph.create_first_event(self.signing_key)
        self.hashgraph.add_first_event(event)

        self.new = []  # list of messages

    @property
    def n(self):
        return len(self.neighbours) + 1

    @classmethod
    def create(cls):
        """Creates new node.
        Generate singing and verification keys. ID will be as verification key."""
        signing_key = SigningKey.generate()
        return cls(signing_key)

    def set(self, stake):
        self.hashgraph.set_stake(stake)

    def acquaint(self, node):
        """- acquaint with Node"""
        self.neighbours[node.id] = node

    def forget(self, node):
        """Forget neighbour node."""
        del self.neighbours[node.id]

    @property
    def id(self):
        return self.signing_key.verify_key

    def __str__(self):
        return "Node({})".format(self.id)

    def sync(self, node, payload):
        """Update hg and return new event ids in topological order."""

        fingerprint = self.hashgraph.get_fingerprint()

        logging.info("{}.sync:message = \n{}".format(self, pformat(fingerprint)))

        # NOTE: communication channel security must be provided in standard way: SSL
        logging.info("{}.sync: reply acquired:".format(self))

        remote_head, difference = node.ask_sync(self, fingerprint)
        logging.info("  remote_head = {}".format(remote_head))
        logging.info("  difference  = {}".format(difference))

        # TODO move to hashgraph
        new = tuple(toposort([event for event in difference if event.id not in self.hashgraph.lookup_table],
                             # difference.keys() - self.hashgraph.keys(),
                             lambda u: u.parents))

        logging.info("{}.sync:new = \n{}".format(self, pformat(new)))

        # TODO move to hashgraph
        for event in new:
            if self.hashgraph.is_valid_event(event.id, event):  # TODO check?
                self.hashgraph.add_event(event)  # (, h) ??

        # TODO move to hashgraph
        # TODO check DOUBLE add remote_head ?
        if self.hashgraph.is_valid_event(remote_head.id, remote_head):  # TODO move id check to communication part
            event = self.hashgraph.new_event(payload, remote_head, self.signing_key)
            self.hashgraph.add_event(event)
            self.hashgraph.head = event
            h = event.id

        logging.info("{}.sync exits.".format(self))

        return new + (event,)

    def ask_sync(self, node, fingerprint):
        """Respond to someone wanting to sync (only public method)."""

        # TODO: only send a diff? maybe with the help of self.height
        # TODO: thread safe? (allow to run while mainloop is running)

        subset = self.hashgraph.difference(fingerprint)

        # TODO Clear response from internal information !!!

        return self.hashgraph.head, subset

    def heartbeat_callback(self):
        """Main working loop."""

        logging.info("{}.heartbeat...".format(self))

        # payload = [event.id for event in self.new]
        payload = ()  # TODO: it is not used!!! why?
        self.new = []

        logging.debug("{}.payload = {}".format(self, payload))

        # pick a random node to sync with but not me
        if len(list(self.neighbours.values())) == 0:
            logging.error("No known neighbours!")
            return None

        node = choice(list(self.neighbours.values()))
        logging.info("{}.sync with {}".format(self, node))
        new = self.sync(node, payload)

        logging.info("{}.new = {}".format(self, new))

        self.new = list(new)

        self.hashgraph.divide_rounds(new)

        new_c = self.hashgraph.decide_fame()
        self.hashgraph.find_order(new_c)

        logging.info("{}.new_c = {}".format(self, new_c))
        logging.info("{}.heartbeat exits.".format(self))

        # return payload
        return self.new
