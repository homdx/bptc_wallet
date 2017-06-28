from bptc.data.event import Event, Fame
from bptc.data.member import Member
from collections import defaultdict
from typing import Set
from datetime import datetime
import math
import dateutil.parser
import time
from statistics import median

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
            event.is_witness = True


def event_can_can_strongly_see_enough_round_r_witnesses(hashgraph, event: Event, r: int):
    members_with_strongly_seen_witnesses = get_members_with_strongly_seen_witnesses_for_round(hashgraph, event, r)

    # Check if all strongly seen witnesses have enough stake
    strongly_seen_stake = sum([hashgraph.known_members[m].stake for m in members_with_strongly_seen_witnesses])
    return strongly_seen_stake > hashgraph.supermajority_stake


def get_members_with_strongly_seen_witnesses_for_round(hashgraph, event: Event, r: int):
    members_on_paths = get_members_on_paths_to_witnesses_for_round(hashgraph, event, r)

    # Collect all members who's witnesses we can strongly see
    members_with_strongly_seen_witnesses = set()
    for member_id, members in members_on_paths.items():
        stake_on_path = sum([hashgraph.known_members[m].stake for m in members])
        if stake_on_path > hashgraph.supermajority_stake:
            members_with_strongly_seen_witnesses.add(member_id)

    return members_with_strongly_seen_witnesses


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
    for x_round in range(0, max(hashgraph.witnesses)+1):
        # Skip this round if we already decided its fame completely
        if x_round in hashgraph.rounds_with_decided_fame:
            continue

        for y_round in range(x_round+1, max(hashgraph.witnesses)+1):
            for x_id in hashgraph.witnesses[x_round].values():
                # We want to decide the fame of x
                x = hashgraph.lookup_table[x_id]

                for y_id in hashgraph.witnesses[y_round].values():
                    y = hashgraph.lookup_table[y_id]
                    d = y.round - x.round

                    if d == 1:
                        # If there is only one round difference, just vote
                        y.votes[x.id] = event_can_see_event(hashgraph, y, x)
                        print('{} votes {} on {}'.format(y.short_id, y.votes[x.id], x.short_id))
                    else:
                        # If there are multiple rounds difference, collect votes
                        s = get_strongly_seen_witnesses_for_round(hashgraph, y, y.round-1)
                        v, t = get_majority_vote_in_set_for_event(hashgraph, s, x)

                        if d % C > 0:  # This is a normal round
                            if t > hashgraph.supermajority_stake:  # If supermajority, then decide
                                x.is_famous = v
                                print('{} fame decided: {}'.format(x.short_id, x.is_famous))
                                y.votes[x.id] = v
                                print('{} votes {} on {}'.format(y.short_id, v, x.short_id))
                                break
                            else:  # Else, just vote
                                y.votes[x.id] = v
                                print('{} votes {} on {}'.format(y.short_id, v, x.short_id))
                        else:  # This is a coin round
                            if t > hashgraph.supermajority_stake:  # If supermajority, then vote
                                y.votes[x.id] = v
                                print('{} votes {} on {}'.format(y.short_id, v, x.short_id))
                            else:  # Else, flip a coin
                                y.votes[x.id] = decide_randomly_based_on_signature(y.signature)
                                print('{} randomly votes {} on {}'.format(y.short_id, y.votes[x.id], x.short_id))

        # Check if round x was completely decided
        decided_witnesses_in_round_x_count = 0
        for x_id in hashgraph.witnesses[x_round].values():
            if hashgraph.lookup_table[x_id] != Fame.UNDECIDED:
                decided_witnesses_in_round_x_count += 1

        if decided_witnesses_in_round_x_count == len(hashgraph.witnesses[x_round].items()):
            hashgraph.rounds_with_decided_fame.add(x_round)
            print("Fame is completely decided for round {}".format(x_round))


def get_strongly_seen_witnesses_for_round(hashgraph, event: Event, r: int) -> Set[str]:
    members_with_strongly_seen_witnesses = get_members_with_strongly_seen_witnesses_for_round(hashgraph, event, r)
    return set([hashgraph.witnesses[r][m] for m in members_with_strongly_seen_witnesses])


def get_majority_vote_in_set_for_event(hashgraph, s: Set[str], x: Event) -> (bool, int):
    """
    Returns the majority vote and the winning amount of stake that a set of witnesses has for another event
    :param hashgraph:
    :param s:
    :param x:
    :return: Tuple containing the majority vote (bool) and the total stake of the majority vote (int)
    """

    stake_for = 0
    stake_against = 0

    for event_id in s:
        event = hashgraph.lookup_table[event_id]
        if event.votes[x.id]:
            stake_for += hashgraph.known_members[event.verify_key].stake
        else:
            stake_against += hashgraph.known_members[event.verify_key].stake

    return Fame.TRUE if stake_for >= stake_against else Fame.FALSE, stake_for if stake_for >= stake_against else stake_against


def event_can_see_event(hashgraph, event_1: Event, event_2: Event) -> bool:
    """
    Whether event 1 can see event 2
    :param event_1:
    :param event_2:
    :return:
    """

    to_visit = {event_1}
    visited = set()

    while len(to_visit) > 0:
        event = to_visit.pop()
        if event not in visited:

            if event.id == event_2.id:
                return True

            if event.round < event_2.round:
                visited.add(event)
                continue

            if event.parents.self_parent is not None:
                to_visit.add(hashgraph.lookup_table[event.parents.self_parent])
            if event.parents.other_parent is not None:
                to_visit.add(hashgraph.lookup_table[event.parents.other_parent])
            visited.add(event)

    return False


def decide_randomly_based_on_signature(signature: str) -> bool:
    signature_bytes = bytearray(signature, encoding='UTF-8')
    middle_byte = signature_bytes[int(math.floor(len(signature_bytes) / 2))]
    return middle_byte >= 128  # 50:50 chance


def find_order(hg):
    decided_events = set()

    for x_id in hg.unordered_events:
        x = hg.lookup_table[x_id]
        # We want to find the order of x
        # Look for a round in which all famous witnesses see r
        for r in range(x.round+1, max(hg.witnesses)+1):
            # Only use rounds that have fully decided fame
            if r not in hg.rounds_with_decided_fame:
                continue

            # x is an ancestor of all famous witnesses of round r
            witnesses = [hg.lookup_table[w] for w in hg.witnesses[r].values()]
            all_famous_witnesses_can_see_x = all([event_can_see_event(hg, w, x) or w.is_famous != Fame.TRUE for w in witnesses])

            # ("this is not true of any round earlier than r" because we count up the rounds
            # If there was an earlier round, we would not reach this point

            if all_famous_witnesses_can_see_x:
                x.round_received = r
                x.consensus_time = get_consensus_time(hg, x).isoformat()

                print("Decided for {}: round_received = {}, time = {}".format(x.short_id, x.round_received, x.consensus_time))

                decided_events.add(x)

    sorted_events = sorted(decided_events, key=lambda e: (e.round_received, e.consensus_time, e.id))
    for e in sorted_events:
        hg.unordered_events.remove(e.id)
        hg.ordered_events.append(e.id)


def get_consensus_time(hg, x) -> datetime:
    times = [dateutil.parser.parse(e.time) for e in get_events_for_consensus_time(hg, x)]
    timestamps = [int(time.mktime(t.timetuple())) for t in times]
    median_timestamp = int(median(timestamps))
    return datetime.fromtimestamp(median_timestamp)


def get_events_for_consensus_time(hg, x) -> Set[Event]:
    """
    "set of each event z such that z is a self-ancestor of a round r unique famous witness,
    and x is an ancestor of z but not of the self-parent of z"
    :param hg: The hashgraph
    :param x: The event for which we want to calculate the median timestamp
    :return:
    """
    result = set()

    # For all famous round r witnesses
    r = x.round_received
    for witness_id in hg.witnesses[r].values():
        witness = hg.lookup_table[witness_id]
        if witness.is_famous != Fame.TRUE:
            continue

        # Go through the self ancenstors
        z = hg.lookup_table[witness.parents.self_parent]
        if z.parents.self_parent is not None:
            z_self_parent = hg.lookup_table[z.parents.self_parent]

            while not event_can_see_event(hg, z, x) or event_can_see_event(hg, z_self_parent, x):
                z = hg.lookup_table[z.parents.self_parent]
                if z.parents.self_parent is None:  # Special case for the first event - this is not described in the paper
                    break
                else:
                    z_self_parent = hg.lookup_table[z.parents.self_parent]

            result.add(z)
        else: # Special case for the first event - this is not described in the paper
            result.add(z)

    return result

