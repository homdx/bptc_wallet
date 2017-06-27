from bptc.data.event import Event
from bptc.data.member import Member
from collections import defaultdict
from typing import Set

C = 6  # How often a coin round occurs, e.g. 6 for every sixth round


def divide_rounds(hashgraph, events):
    for event in events:
        r = 0

        if event.parents.self_parent is not None:
            r = hashgraph.lookup_table[event.parents.self_parent].round
        if event.parents.other_parent is not None:
            r = max(r, hashgraph.lookup_table[event.parents.other_parent].round)

        if event_can_can_strongly_see_enough_round_r_witnesses(hashgraph, event, r):
            r = r + 1

        event.round = r

        if event.parents.self_parent is None or event.round > hashgraph.lookup_table[event.parents.self_parent].round:
            hashgraph.witnesses[r][event.verify_key] = event.id


def event_can_can_strongly_see_enough_round_r_witnesses(hashgraph, event: Event, r: int):
    members_on_paths = get_members_on_paths_to_witnesses_for_round(hashgraph, event, r)

    # Collect all members who's witnesses we can strongly see
    members_with_strongly_seen_witnesses = set()
    for member_id, members in members_on_paths.items():
        stake_on_path = sum([hashgraph.known_members[m].stake for m in members])
        if stake_on_path > hashgraph.supermajority_stake:
            members_with_strongly_seen_witnesses.add(member_id)

    # Check if all strongly seen witnesses have enough stake
    strongly_seen_stake = sum([hashgraph.known_members[m].stake for m in members_with_strongly_seen_witnesses])
    return strongly_seen_stake > hashgraph.supermajority_stake


def get_members_on_paths_to_witnesses_for_round(hashgraph, start_event: Event, r: int):
    # {member_id -> set(member_id)}: For each member, the set of members through which the paths to the member's
    #                                previous witness lead
    result = defaultdict(set)

    def visit_event(event: Event, visited_members: Set[Member]):
        # Stop once we reach the previous round
        if event.id != start_event.id and event.round < r:
            return

        # Add events creator to visited members
        visited_members.add(event.verify_key)

        # Check if event is witness of correct round
        if event.verify_key in hashgraph.witnesses[r] and event.id == hashgraph.witnesses[r][event.verify_key]:
            # We reached a witness - add the list of visited members to the result
            result[event.verify_key] |= visited_members

        # Continue searching with parents
        # A witness might have a path to another witness of the same round, so we can't stop just because
        # we found a witness
        if event.parents.self_parent is not None:
            visit_event(hashgraph.lookup_table[event.parents.self_parent], set(visited_members))
        if event.parents.other_parent is not None:
            visit_event(hashgraph.lookup_table[event.parents.other_parent], set(visited_members))

    visit_event(start_event, set())

    return result


def decide_fame(hashgraph):
    pass


def find_order(self, new_c):
    pass
