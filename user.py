from hashgraph import Hashgraph
from sklavit_nacl.signing import *
import logging
from random import choice
from utils import toposort
from pprint import pformat
from event import Event

logger = logging.getLogger(__name__)


class User:
    """
    A user in a hashgraph network.

    Note can:
    - process incoming requests.
    - generate requests

    User <==> User <==> User

    Network == set of working Users

    User -- User:
    - create
    - dump/load identity
    - start (and connect to network), ready to process requests
    - shutdown
    -----
    - acquaint with User
    - forget User
    -----
    - get (full) state; get consensus as sub-request
    - send message
    - subscribe / unsubscribe listener
    -----

    User -- User:
    - ping ?; return ping time
    - get( what to get ?); returns response
    - post(message); returns response
    - pinged_get
    - pinged_post
    """

    def __init__(self, signing_key):
        self.signing_key = signing_key  # TODO implement

        self.neighbours = {}  # dict(pk -> User)
        self.hashgraph = Hashgraph()

        # init first local event
        self.head = None
        event = self.create_first_event()
        self.hashgraph.add_first_event(event)
        self.head = event

    @classmethod
    def create(cls):
        """Creates new user.
        Generate singing and verification keys. ID will be as verification key."""
        signing_key = SigningKey.generate()
        return cls(signing_key)

    def set(self, stake):
        self.hashgraph.set_stake(stake)

    def acquaint(self, user):
        """- acquaint with User"""
        self.neighbours[user.id] = user

    def forget(self, user):
        """Forget neighbour user."""
        del self.neighbours[user.id]

    @property
    def id(self):
        return self.signing_key.verify_key

    def __str__(self):
        return "User({})".format(self.id)

    def sync(self, user, payload):
        """Update hg and return new event ids in topological order."""

        fingerprint = self.hashgraph.get_fingerprint()

        logger.info("{}.sync:message = \n{}".format(self, pformat(fingerprint)))

        # NOTE: communication channel security must be provided in standard way: SSL
        logger.info("{}.sync: reply acquired:".format(self))

        remote_head, difference = user.ask_sync(self, fingerprint)
        logger.info("  remote_head = {}".format(remote_head))
        logger.info("  difference  = {}".format(difference))

        # TODO move to hashgraph
        new = tuple(toposort([event for event in difference if event.id not in self.hashgraph.lookup_table],
                             # difference.keys() - self.hashgraph.keys(),
                             lambda u: u.parents))

        logger.info("{}.sync:new = \n{}".format(self, pformat(new)))

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

        logger.info("{}.sync exits.".format(self))

        return new + (event,)

    def ask_sync(self, user, fingerprint):
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

        # pick a random user to sync with but not me
        if len(list(self.neighbours.values())) == 0:
            logger.error("No known neighbours!")
            return None

        user = choice(list(self.neighbours.values()))
        logger.info("{}.sync with {}".format(self, user))
        new = self.sync(user, payload)

        logger.info("{}.new = {}".format(self, new))

        self.new = list(new)

        self.hashgraph.divide_rounds(new)

        new_c = self.hashgraph.decide_fame()
        self.hashgraph.find_order(new_c)

        logger.info("{}.new_c = {}".format(self, new_c))
        logger.info("{}.heartbeat exits.".format(self))

        # return payload
        return self.new

    def heartbeat(self):
        logger.info("{} heartbeat...".format(self))
        event = self._new_event(None, (self.head, None))
        self.hashgraph.add_event(event)
        self.head = event
        return event

    def create_first_event(self):
        event = self._new_event(None, (self.head, None))
        event.parents = (event, None)
        event.round = 0
        event.can_see = {event.verify_key: event}
        return event

    def _new_event(self, data, parents):
        # TODO: fail if an ancestor of p[1] from creator self.pk is not an ancestor of p[0] ???
        event = Event(self.signing_key, data, parents)
        logger.info("{} created new event {}".format(self, event))
        return event
