import datetime
"""
Warning:
The pickle module is not secure against erroneous or maliciously constructed data.
Never unpickle data received from an untrusted or unauthenticated source.
https://docs.python.org/2/library/pickle.html
"""
import pickle  # TODO: remove
from nacl.bindings import crypto_hash_sha512
from nacl.encoding import Base64Encoder


class Event(object):  # TODO make it namedtuple
    """Event is a node of hashgraph."""

    def __init__(self, signing_key, data, parents, time=None):
        # Immutable body of Event
        self.data = data
        self.parents = parents
        self.time = datetime.datetime.now() if time is None else time
        self.verify_key = signing_key.verify_key  # Setting of verify_key is delayed TODO fix it!
        # End of immutable body
        self.parents_filtered = tuple(filter(lambda p: p is not None, self.parents))
        parents_ids = [parent.id for parent in self.parents_filtered]
        self.__body = pickle.dumps((self.data, parents_ids, self.time, self.verify_key))

        # Sign Event body.
        self.signature = signing_key.sign(self.__body).signature

        # Compute Event hash and ID.
        h = Base64Encoder.encode(crypto_hash_sha512(self.__body)).decode()
        self.__id = h[:5]  # TODO fix this limit

        # assigned round number of each event
        self.round = None  # TODO

        # {event-hash => bool}
        self.votes = dict()  # TODO only votes are Graph node-specific????

        # 0 or 1 + max(height of parents)
        if self.parents_filtered == ():
            self.height = 0
        else:
            self.height = max(parent.height for parent in self.parents_filtered) + 1

        # {node-id = > event}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see
        self.can_see = {}

    def __str__(self):
        if len(self.parents_filtered) == 0:
            parent_str = '[None, None]'
        elif len(self.parents_filtered) == 1:
            parent_str = '[' + self.parents[0].id + ', None]'
        else:
            parent_str = [p.id for p in self.parents]
        return "Event({}) by User({}), Height({}), Round({}), Parents({}), Data({})".format(
            self.id[:6], self.verify_key, self.height, self.round, parent_str, self.data)

    def __repr__(self):
        return self.__str__()

    @property
    def body(self):
        return self.__body

    @property
    def id(self):
        return self.__id

