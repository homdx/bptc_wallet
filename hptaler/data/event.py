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
from hptaler.data.transaction import Transaction
from typing import Dict, List, Tuple
import json

# The parents of an event
Parents = collections.namedtuple('Parents', 'self_parent other_parent')


class Event:
    """
    An Event is a node in the hashgraph - it may contain transactions
    """

    def __init__(self, verify_key, data: List[Transaction], parents: Parents, time=None):
        # Immutable body of Event
        self.data = data
        self.parents = parents
        self.time: datetime = datetime.datetime.now().isoformat() if time is None else time
        self.verify_key: VerifyKey = verify_key
        # End of immutable body

        # Calculate the body (relevant data for hashing and signing)
        self.__body = pickle.dumps((self.data, parents, self.time, self.verify_key))

        # Compute Event hash and ID
        self.__id = Base64Encoder.encode(crypto_hash_sha512(self.__body)).decode("utf-8")

        # Event is always created with height 0
        # The real height is determined once the event is added to the hashgraph
        self.height: int = 0

        # assigned round number of each event
        self.round: int = None  # TODO

        # {event-hash => bool}
        self.votes: Dict[str, bool] = dict()

        # {node-id = > event}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see

        # {member-id => event-hash}: The top event of each member that this event can see
        self.can_see = dict()

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
    def from_dict(cls, dict_event) -> "Event":
        data = None
        if dict_event['data'] is not None:
            data = [Transaction.from_dict(x) for x in dict_event['data']]

        event = Event(VerifyKey.from_base64_string(dict_event['verify_key']),
                      data, Parents(dict_event['parents'][0], dict_event['parents'][1]), dict_event['time'])
        event.height = dict_event['height']
        event.signature = Base64Encoder.decode(dict_event['signature'].encode('utf-8'))
        return event

    @classmethod
    def from_debug_dict(cls, dict_event) -> "Event":
        data = None
        if dict_event['data'] is not None:
            data = [Transaction.from_dict(x) for x in dict_event['data']]

        event = Event(VerifyKey.from_base64_string(dict_event['verify_key']),
                      data, Parents(dict_event['parents'][0], dict_event['parents'][1]), dict_event['time'])
        event.height = dict_event['height']
        event.signature = Base64Encoder.decode(dict_event['signature'].encode('utf-8'))
        event.round = dict_event['round']
        return event

    def to_dict(self) -> Dict:
        return dict(
            data=[x.to_dict() for x in self.data] if self.data is not None else None,
            parents=self.parents,
            height=self.height,
            time=self.time,
            verify_key=self.verify_key.encode(encoder=Base64Encoder).decode("utf-8"),
            signature=Base64Encoder.encode(self.signature).decode("utf-8")
        )

    def to_debug_dict(self) -> Dict:
        return dict(
            data=[x.to_dict() for x in self.data] if self.data is not None else None,
            parents=self.parents,
            height=self.height,
            time=self.time,
            verify_key=self.verify_key.encode(encoder=Base64Encoder).decode("utf-8"),
            signature=Base64Encoder.encode(self.signature).decode("utf-8"),
            round=self.round
        )

    def to_db_tuple(self) -> Tuple:
        return (
            self.id,
            json.dumps([x.to_dict() for x in self.data]) if self.data is not None else None,
            self.parents.self_parent,
            self.parents.other_parent,
            self.time,
            self.verify_key.to_base64_string(),
            self.height,
            Base64Encoder.encode(self.signature).decode("utf-8")
        )

    @classmethod
    def from_db_tuple(cls, e: Tuple) -> "Event":
        data = None
        if e[1] is not None:
            data = [Transaction.from_dict(x) for x in json.loads(e[1])]

        event = Event(VerifyKey.from_base64_string(e[5]),
                      data,
                      Parents(e[2], e[3]),
                      e[4])

        event.height = e[6]
        event.signature = Base64Encoder.decode(e[7].encode('utf-8'))

        return event

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
