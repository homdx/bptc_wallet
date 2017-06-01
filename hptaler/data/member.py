from utilities.signing import SigningKey


class Member:
    """
    A Member is a participant in the Hashgraph
    """

    def __init__(self, verify_key):
        # The key used to sign data
        self.signing_key = None

        # The key to verify data
        self.verify_key = verify_key

        # The networking data
        # TODO: Set, or move somewhere else
        self.ip = None
        self.port = None

    @classmethod
    def create(cls) -> 'Member':
        """
        Creates new member with a signing (private) key
        """
        signing_key = SigningKey.generate()
        new_member = Member(signing_key.verify_key)
        new_member.signing_key = signing_key
        return new_member

    @property
    def id(self):
        return self.verify_key

    def __str__(self):
        return "Member({})".format(self.id)
