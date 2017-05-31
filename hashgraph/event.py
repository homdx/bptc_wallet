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
import collections

Parents = collections.namedtuple('Parents', 'self_parent other_parent')
SerializableEvent = collections.namedtuple('SerializableEvent', 'data parents height time verify_key')


class Event(object):  # TODO make it namedtuple
    """Event is a node of hashgraph."""

    def __init__(self, verify_key, data, parents: SerializableEvent, time=None):
        # Immutable body of Event
        self.data = data
        self.parents = parents
        self.time = datetime.datetime.now().isoformat() if time is None else time
        self.verify_key = str(verify_key)  # Setting of verify_key is delayed TODO fix it!
        # End of immutable body
        self.__body = pickle.dumps((self.data, parents, self.time, self.verify_key))

        # Compute Event hash and ID.
        h = Base64Encoder.encode(crypto_hash_sha512(self.__body)).decode()
        self.__id = h[:5]  # TODO fix this limit
        self.height = 0
        # assigned round number of each event
        self.round = None  # TODO

        # {event-hash => bool}
        # self.votes = dict()  # TODO only votes are Graph node-specific????

        # {node-id = > event}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see

        # {event-hash => event}: All events that this event can see
        self.can_see = {}

    def __str__(self):
        return "Event({}) by Member({}), Height({}), Round({}), {}, Data({}), Time({})".format(
            self.id, self.verify_key, self.height, self.round, self.parents, self.data, self.time)

    def __repr__(self):
        return self.__str__()

    @property
    def body(self):
        return self.__body

    @property
    def id(self):
        return self.__id

    @classmethod
    def create_from(cls, s_event):
        # 0: data, 1: parents, 2: height, 3: time, 4: verify_key
        event = Event(s_event[4], s_event[0], Parents(s_event[1][0], s_event[1][1]), s_event[3])
        event.height = s_event[2]
        return event
