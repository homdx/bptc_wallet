from typing import Tuple

from libnacl import crypto_sign_keypair
from libnacl.encode import base64_encode
from twisted.internet.address import IPv4Address

from bptc.utils import logger


class Member:
    """
    A Member is a participant in the Hashgraph
    """

    def __init__(self, verify_key, signing_key):
        # The key used to sign data
        self.signing_key = signing_key

        # The key to verify data
        self.verify_key = verify_key

        # The current (cached) head of this member
        # Currently only used for the own member - all others are calculated on the fly
        self.head = None

        # The current stake of this member
        self.stake = 1  # TODO: Different stakes

        # The networking data
        self.address = None

    @classmethod
    def create(cls) -> 'Member':
        """
        Creates new member with a signing (private) key
        """
        verify_key_bytes, signing_key_bytes = crypto_sign_keypair()
        verify_key = base64_encode(verify_key_bytes).decode("UTF-8")
        signing_key = base64_encode(signing_key_bytes).decode("UTF-8")
        new_member = Member(verify_key, signing_key)

        logger.info("Created new Member: " + str(new_member))

        return new_member

    @property
    def id(self):
        return self.verify_key

    def __str__(self):
        return "Member({}...)".format(self.id[:6])

    def to_verifykey_string(self):
        return self.verify_key

    @classmethod
    def from_db_tuple(cls, db: Tuple) -> "Member":
        member = Member(db[0], None)
        member.signing_key = db[1] if db[1] is not None else None
        member.head = db[2]  # TODO: Make this an Event object
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

        return (self.verify_key,
                self.signing_key if self.signing_key is not None else None,
                self.head,
                self.stake,
                host,
                port)
