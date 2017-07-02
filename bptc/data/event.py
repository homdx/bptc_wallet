import datetime
import collections
from collections import OrderedDict
from bptc.data.transaction import Transaction
from typing import Dict, List, Tuple
import json
from libnacl import crypto_hash_sha512, crypto_sign_open, crypto_sign
from libnacl.encode import base64_encode, base64_decode


# The parents of an event
class Parents(collections.namedtuple("Parents", ["self_parent", "other_parent"])):

    def __str__(self):
        return 'Parents(self_parent: {}, other_parent: {})'.format(
            None if self.self_parent is None else self.self_parent[:6] + '...',
            None if self.other_parent is None else self.other_parent[:6] + '...')


class Fame:
    UNDECIDED = -1
    FALSE = 0
    TRUE = 1


class Event:
    """
    An Event is a node in the hashgraph - it may contain transactions
    """

    def __init__(self, verify_key, data: List[Transaction], parents: Parents, time=None):
        # Immutable body of Event
        self.data = data
        self.parents = parents
        self.time = datetime.datetime.now().isoformat() if time is None else time
        self.verify_key = verify_key
        # End of immutable body

        # Compute Event hash and ID
        self.__id = base64_encode(crypto_hash_sha512(self.body.encode("UTF-8"))).decode("UTF-8")

        # Event is always created with height 0
        # The real height is determined once the event is added to the hashgraph
        self.height = 0

        # assigned round number of each event
        self.round = 0

        # {event-hash => bool}
        self.votes = dict()

        # {node-id = > event}}: stores for each event ev
        # and for each member m the latest event from m having same round
        # number as ev that ev can see

        # The signature is empty at the beginning - use sign() to sign the event once it is finished
        self.signature = None

        # Whether this event is a witness
        self.is_witness = False

        # Whether this event is famous
        self.is_famous = Fame.UNDECIDED

        # Ordering info
        self.round_received = None
        self.consensus_time = None

        # DEBUGGING
        self.processed_by_divideRounds = None

    def __str__(self):
        return "Event({}...) by Member({}...), Height({}), Round({}), {}, Data({}), Time({})".format(
            self.id[:6], self.verify_key[:6], self.height, self.round, self.parents, self.data, self.time)

    def __repr__(self):
        return self.__str__()

    @property
    def body(self):
        return json.dumps(OrderedDict([
            ('data', [x.to_dict() for x in self.data] if self.data is not None else None),
            ('self_parent', self.parents.self_parent),
            ('other_parent', self.parents.other_parent),
            ('time', self.time),
            ('verify_key', self.verify_key)]
        ))

    @property
    def id(self):
        return self.__id

    @property
    def short_id(self):
        return self.id[:6]

    @classmethod
    def from_dict(cls, dict_event) -> "Event":
        data = None
        if dict_event['data'] is not None:
            data = [Transaction.from_dict(x) for x in dict_event['data']]

        event = Event(dict_event['verify_key'],
                      data, Parents(dict_event['parents'][0], dict_event['parents'][1]), dict_event['time'])
        event.height = dict_event['height']
        event.signature = dict_event['signature']
        event.is_witness = dict_event['witness']
        event.is_famous = dict_event['is_famous']
        event.round_received = dict_event['round_received']
        event.consensus_time = dict_event['consensus_time']
        return event

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('data', [x.to_dict() for x in self.data] if self.data is not None else None),
            ('parents', self.parents),
            ('height', self.height),
            ('time', self.time),
            ('verify_key', self.verify_key),
            ('signature', self.signature),
            ('witness', self.is_witness),
            ('is_famous', self.is_famous),
            ('round_received', self.round_received),
            ('consensus_time', self.consensus_time),
            ('round', self.round)
        ])

    def to_db_tuple(self) -> Tuple:
        return (
            self.id,
            json.dumps([x.to_dict() for x in self.data]) if self.data is not None else None,
            self.parents.self_parent,
            self.parents.other_parent,
            self.time,
            self.verify_key,
            self.height,
            self.signature,
            self.round,
            self.is_witness,
            self.is_famous,
            self.round_received,
            self.consensus_time
        )

    @classmethod
    def from_db_tuple(cls, e: Tuple) -> "Event":
        data = None
        if e[1] is not None:
            data = [Transaction.from_dict(x) for x in json.loads(e[1])]

        event = Event(e[5],
                      data,
                      Parents(e[2], e[3]),
                      e[4])

        event.height = e[6]
        event.signature = e[7]
        event.round = e[8]
        event.is_witness = e[9]
        event.is_famous = e[10]
        event.round_received = e[11]
        event.consensus_time = e[12]

        return event

    def sign(self, signing_key) -> None:
        """
        Signs an event with the given signing key, setting its signature
        :param signing_key: The signing key to use
        :return: None
        """
        signing_key_byte = base64_decode(signing_key.encode("UTF-8"))
        self.signature = base64_encode(crypto_sign(self.body.encode("UTF-8"), signing_key_byte)).decode("UTF-8")

    @property
    def has_valid_signature(self) -> bool:
        """
        Checks whether the event has a valid signature
        :return: bool
        """
        signature_byte = base64_decode(self.signature.encode("UTF-8"))
        verify_key_byte = base64_decode(self.verify_key.encode("UTF-8"))
        try:
            message = crypto_sign_open(signature_byte, verify_key_byte)
            return message.decode('UTF-8') == self.body
        except ValueError:
            return False
