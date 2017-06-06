import datetime
from nacl.exceptions import BadSignatureError
"""
Warning:
The pickle module is not secure against erroneous or maliciously constructed data.
Never unpickle data received from an untrusted or unauthenticated source.
https://docs.python.org/2/library/pickle.html
"""
import pickle
from nacl.bindings import crypto_hash_sha512
from nacl.encoding import Base64Encoder
from utilities.signing import VerifyKey
import collections

# The parents of an event
Parents = collections.namedtuple('Parents', 'self_parent other_parent')

# A serializable version of an event for inter-member communication
SerializableEvent = collections.namedtuple('SerializableEvent', 'data parents height time verify_key signature')

# A serializable version of an event for debugging and visualization (contains more information)
SerializableDebugEvent = collections.namedtuple('SerializableEvent', 'data parents height time verify_key signature round')


class Event:
    """
    An Event is a node in the hashgraph - it may contain transactions
    """

    def __init__(self, verify_key, data, parents: Parents, time=None):
        # Immutable body of Event
        self.data = data
        self.parents = parents
        self.time = datetime.datetime.now().isoformat() if time is None else time
        self.verify_key = verify_key
        # End of immutable body

        # Calculate the body (relevant data for hashing and signing)
        self.__body = pickle.dumps((self.data, parents, self.time, self.verify_key))

        # Compute Event hash and ID
        self.__id = Base64Encoder.encode(crypto_hash_sha512(self.__body)).decode("utf-8")

        # Event is always created with height 0
        # The real height is determined once the event is added to the hashgraph
        self.height = 0

        # assigned round number of each event
        self.round = None  # TODO

        # {event-hash => bool}
        self.votes = dict()

        # {node-id = > event}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see

        # {member-id => event-hash}: The top event of each member that this event can see
        self.can_see = {}

        # The signature is empty at the beginning - use sign() to sign the event once it is finished
        self.signature = None

    def __str__(self):
        return "Event({}...) by Member({}), Height({}), Round({}), {}, Data({}), Time({})".format(
            self.id[:6], self.verify_key, self.height, self.round, self.parents, self.data, self.time)

    def __repr__(self):
        return self.__str__()

    @property
    def body(self):
        return self.__body

    @property
    def id(self):
        return self.__id

    @classmethod
    def from_serializable_event(cls, s_event):
        # 0: data, 1: parents, 2: height, 3: time, 4: verify_key, 5: signature
        event = Event(VerifyKey(s_event[4].encode("utf-8"), encoder=Base64Encoder), s_event[0],
                      Parents(s_event[1][0],s_event[1][1]), s_event[3])
        event.height = s_event[2]
        event.signature = Base64Encoder.decode(s_event[5].encode("utf-8"))
        return event

    @classmethod
    def from_serializable_debug_event(cls, s_event):
        # 0: data, 1: parents, 2: height, 3: time, 4: verify_key, 5: signature, 6: round
        event = Event(VerifyKey(s_event[4].encode("utf-8"), encoder=Base64Encoder), s_event[0],
                      Parents(s_event[1][0], s_event[1][1]), s_event[3])
        event.height = s_event[2]
        event.signature = Base64Encoder.decode(s_event[5].encode("utf-8"))
        event.round = s_event[6]
        return event

    def to_serializable_event(self):
        return SerializableEvent(self.data, self.parents, self.height, self.time,
                                 self.verify_key.encode(encoder=Base64Encoder).decode("utf-8"),
                                 Base64Encoder.encode(self.signature).decode("utf-8"))

    def to_serializable_debug_event(self):
        return SerializableDebugEvent(self.data, self.parents, self.height, self.time,
                                      self.verify_key.encode(encoder=Base64Encoder).decode("utf-8"),
                                      Base64Encoder.encode(self.signature).decode("utf-8"), self.round)

    def sign(self, signing_key) -> None:
        """
        Signs an event with the given signing key, setting its signature
        :param signing_key: The signing key to use
        :return: None
        """
        self.signature = signing_key.sign(self.body).signature

    @property
    def has_valid_signature(self) -> bool:
        """
        Checks whether the event has a valid signature
        :return: bool
        """
        try:
            self.verify_key.verify(self.body, self.signature)
            return True
        except BadSignatureError:
            return False
