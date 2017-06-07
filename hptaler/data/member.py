from utilities.signing import SigningKey, VerifyKey
from utilities.log_helper import logger
from twisted.internet.address import IPv4Address
from typing import Tuple
from hptaler.data.event import Event


class Member:
    """
    A Member is a participant in the Hashgraph
    """

    def __init__(self, verify_key: VerifyKey):
        # The key used to sign data
        self.signing_key: SigningKey = None

        # The key to verify data
        self.verify_key: VerifyKey = verify_key

        # The current (cached) head of this member
        # Currently only used for the own member - all others are calculated on the fly
        self.head: Event = None

        # The current stake of this member
        self.stake: int = 1  # TODO: Different stakes

        # The networking data
        self.address: IPv4Address = None

    @classmethod
    def create(cls) -> 'Member':
        """
        Creates new member with a signing (private) key
        """
        signing_key = SigningKey.generate()
        new_member = Member(signing_key.verify_key)
        new_member.signing_key = signing_key

        logger.info("Created new Member: " + str(new_member))

        return new_member

    @property
    def id(self):
        return self.verify_key

    def __str__(self):
        return "Member({})".format(self.id)

    @classmethod
    def from_verifykey_string(cls, string_verify_key):
        verify_key = VerifyKey.from_base64_string(string_verify_key)
        return cls(verify_key)

    def to_verifykey_string(self):
        return self.verify_key.to_base64_string()

    @classmethod
    def from_db_tuple(cls, db: Tuple) -> "Member":
        member = Member.from_verifykey_string(db[0])
        member.signing_key = SigningKey.from_base64_string(db[1]) if db[1] is not None else None
        member.head = db[2] # TODO: Make this an Event object
        member.stake = db[3]
        if db[4] is not None and db[5] is not None:
            member.address = IPv4Address('TCP', db[4], db[5])

        return member

    def to_db_tuple(self) -> Tuple:
        host = None
        port = None
        if self.address is not None:
            host = self.address.host
            port = self.address.port

        return (self.verify_key.to_base64_string(),
                self.signing_key.to_base64_string() if self.signing_key is not None else None,
                self.head,
                self.stake,
                host,
                port)
