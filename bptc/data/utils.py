from typing import List
from bptc.data.member import Member


def filter_members_with_address(members: List[Member]) -> List[Member]:
    """
    Filters a list of members, only returning those who have a known network address
    :param members: The list of members to be filtered
    :return: The filtered lise
    """
    return [m for m in members if m.address is not None]
