import datetime
import pickle
from nacl.bindings import crypto_hash_sha512
from nacl.encoding import Base64Encoder


class Event(object):  # TODO make it namedtuple
    """Event is a node of hashgraph."""

    def __init__(self, signing_key, d, parents, t=None):
        # Immutable body of Event
        self.d = d
        self.parents = parents
        self.t = datetime.datetime.now() if t is None else t
        self.verify_key = signing_key.verify_key  # Setting of verify_key is delayed TODO fix it!
        # End of immutable body
        parents_ids = [parent.id for parent in self.parents]
        self.__body = pickle.dumps((self.d, parents_ids, self.t, self.verify_key))

        # Sign Event body.
        self.signature = signing_key.sign(self.__body).signature

        # Compute Event hash and ID.
        h = Base64Encoder.encode(crypto_hash_sha512(self.__body)).decode()
        self.__id = h[:5]  # TODO fix this limit

        # assigned round number of each event
        self.round = None

        # {event-hash => bool}
        self.votes = dict()  # TODO only votes are Graph node-specific????

        # 0 or 1 + max(height of parents)
        if parents == ():
            self.height = 0
        else:
            self.height = max(parent.height for parent in parents) + 1

        # {node-id = > event}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see
        self.can_see = {}

    def __str__(self):
        return "{{Event}}{}... by {}, H{}, R{}, P{}, D{}".format(
            self.id[:6], self.verify_key, self.height, self.round, [p.id for p in self.parents], self.d)

    def __repr__(self):
        return self.__str__()

    @property
    def body(self):
        return self.__body

    @property
    def id(self):
        return self.__id

