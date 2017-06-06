from utilities.signing import SigningKey, VerifyKey
from nacl.encoding import Base64Encoder

from utilities.log_helper import logger


class Member:
    """
    A Member is a participant in the Hashgraph
    """

    def __init__(self, verify_key: VerifyKey):
        # The key used to sign data
        self.signing_key = None

        # The key to verify data
        self.verify_key = verify_key

        # The current (cached) head of this member
        # Currently only used for the own member - all others are calculated on the fly
        self.head = None

        # The current stake of this member
        self.stake = 1  # TODO: Different stakes

        # The networking data
        # TODO: Set, or move somewhere else
        self.address = None

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

    @classmethod
    def from_string_verifykey(cls, string_verify_key):
        verify_key = VerifyKey(string_verify_key.encode("utf-8"), encoder=Base64Encoder)
        return cls(verify_key)

    @property
    def id(self):
        return self.verify_key

    def __str__(self):
        return "Member({})".format(self.id)
