import bptc
from bptc.data.event import Event, Fame
from bptc.data.member import Member
from collections import defaultdict
from typing import Set
from datetime import datetime
import math
import dateutil.parser
import time
from statistics import median
from bptc.utils.toposort import toposort


# DIVIDE ROUNDS

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

        # DEBUG
        event.processed_by_divideRounds = True


def event_can_can_strongly_see_enough_round_r_witnesses(hashgraph, event: Event, r: int):
    members_with_strongly_seen_witnesses = get_members_with_strongly_seen_witnesses_for_round(hashgraph, event, r)

    # Check if all of those members have enough stake
    strongly_seen_stake = sum([hashgraph.known_members[m].stake for m in members_with_strongly_seen_witnesses])
    return strongly_seen_stake > hashgraph.supermajority_stake


def get_members_with_strongly_seen_witnesses_for_round(hashgraph, event: Event, r: int):
    members_on_paths = fast_get_members_on_paths_to_witnesses_for_round(hashgraph, event, r)
    #old_members_on_paths = get_members_on_paths_to_witnesses_for_round(hashgraph, event, r)

    #same = len(members_on_paths) == len(old_members_on_paths) and all([len(s) == len(o_s) for s, o_s in zip(members_on_paths, old_members_on_paths)])

    #if not same:
    #    print("Fast member on paths was not equal!")

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


def fast_get_members_on_paths_to_witnesses_for_round(hashgraph, start_event: Event, r: int):
    # for every ancestor, the nodes that were visited to read it
    members_on_paths = defaultdict(set)
    members_on_paths[start_event.id].add(start_event.verify_key)
    visited, queue = set(), [start_event]

    while queue:
        event = queue.pop(0)

        # Stop once we reach the previous round
        if event.id != start_event.id and event.round < r:
            continue

        if event not in visited:
            visited.add(event)

            if event.parents.self_parent is not None:
                self_parent = hashgraph.lookup_table[event.parents.self_parent]
                members_on_paths[self_parent.id].add(self_parent.verify_key)
                members_on_paths[self_parent.id].add(event.verify_key)
                members_on_paths[self_parent.id] |= members_on_paths[event.id]
                queue.append(self_parent)

            if event.parents.other_parent is not None:
                other_parent = hashgraph.lookup_table[event.parents.other_parent]
                members_on_paths[other_parent.id].add(other_parent.verify_key)
                members_on_paths[other_parent.id].add(event.verify_key)
                members_on_paths[other_parent.id] |= members_on_paths[event.id]
                queue.append(other_parent)

    # Only witnesses are relevant
    result = defaultdict(set)
    for member_id, witness_id in hashgraph.witnesses[r].items():
        if len(members_on_paths[witness_id]) > 0:
            result[member_id] = members_on_paths[witness_id]

    return result


# DECIDE FAME

def decide_fame(hashgraph):
    for x_round in range(0, max(hashgraph.witnesses)+1):
        # Skip this round if we already decided its fame completely
        if x_round in hashgraph.rounds_with_decided_fame:
            continue

        x_events = {e: hashgraph.lookup_table[e] for e in hashgraph.witnesses[x_round].values()}
        for x in toposort(x_events):
            for y_round in range(x_round+1, max(hashgraph.witnesses)+1):
                y_events = {e: hashgraph.lookup_table[e] for e in hashgraph.witnesses[y_round].values()}
                for y in toposort(y_events):
                    d = y.round - x.round

                    if d == 1:
                        # If there is only one round difference, just vote
                        y.votes[x.id] = event_can_see_event(hashgraph, y, x)
                        # print('{} votes {} on {}'.format(y.short_id, y.votes[x.id], x.short_id))
                    else:
                        # If there are multiple rounds difference, collect votes
                        s = get_strongly_seen_witnesses_for_round(hashgraph, y, y.round-1)
                        v, t = get_majority_vote_in_set_for_event(hashgraph, s, x)

                        if d % bptc.C > 0:  # This is a normal round
                            if t > hashgraph.supermajority_stake:  # If supermajority, then decide
                                x.is_famous = v
                                # print('{} fame decided: {}'.format(x.short_id, x.is_famous))
                                y.votes[x.id] = v
                                # print('{} votes {} on {}'.format(y.short_id, v, x.short_id))
                                break
                            else:  # Else, just vote
                                y.votes[x.id] = v
                                # print('{} votes {} on {}'.format(y.short_id, v, x.short_id))
                        else:  # This is a coin round
                            if t > hashgraph.supermajority_stake:  # If supermajority, then vote
                                y.votes[x.id] = v
                                # print('{} votes {} on {}'.format(y.short_id, v, x.short_id))
                            else:  # Else, flip a coin
                                y.votes[x.id] = decide_randomly_based_on_signature(y.signature)
                                # print('{} randomly votes {} on {}'.format(y.short_id, y.votes[x.id], x.short_id))

        # Check if round x was completely decided
        if all([hashgraph.lookup_table[event_id].is_famous != Fame.UNDECIDED for event_id in hashgraph.witnesses[x_round].values()]):
            hashgraph.rounds_with_decided_fame.add(x_round)
            bptc.logger.debug("Fame is completely decided for round {}".format(x_round))


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
        if x.id in event.votes and event.votes[x.id]:
            stake_for += hashgraph.known_members[event.verify_key].stake
        else:
            stake_against += hashgraph.known_members[event.verify_key].stake

    return Fame.TRUE if stake_for >= stake_against else Fame.FALSE, stake_for if stake_for >= stake_against else stake_against


def event_can_see_event(hg, event_1: Event, event_2: Event) -> bool:
    """
    Whether event 1 can see event 2
    :param hashgraph:
    :param event_1:
    :param event_2:
    :return:
    """

    # Only calculate if the answer is not already cached
    if event_2.id in event_1.can_see_cache:
        return event_1.can_see_cache[event_2.id]
    else:
        if parents_are_forked(hg, event_1) or event_1.round < event_2.round:
            event_1.can_see_cache[event_2.id] = False
            return False

        can_see = False

        if event_1.parents.self_parent is not None:
            can_see = event_can_see_event(hg, hg.lookup_table[event_1.parents.self_parent], event_2)

        if can_see:
            event_1.can_see_cache[event_2.id] = True
            return True

        if event_1.parents.other_parent is not None:
            can_see = event_can_see_event(hg, hg.lookup_table[event_1.parents.other_parent], event_2)

        event_1.can_see_cache[event_2.id] = can_see
        return can_see


def parents_are_forked(hg, event: Event):
    """
    Let w, x, y be events and x and y are ancestors of w. Let x and y be events of member A,
    but neither of them is a self-ancestor of the other (-> Fork). Then w sees neither x nor y.
    """
    if event.parents.self_parent is None or event.parents.other_parent is None:
        return False

    self_parent = hg.lookup_table[event.parents.self_parent]
    other_parent = hg.lookup_table[event.parents.other_parent]

    if self_parent.verify_key != other_parent.verify_key:
        return False

    current_event, goal_event = (self_parent, other_parent) if self_parent.height > other_parent.height else (other_parent, self_parent)

    # Search if we can find goal_event
    # If so, they can't be forked
    while current_event.parents.self_parent is not None and current_event.height >= goal_event.height:
        if current_event.parents.self_parent == goal_event.id:
            return False
        current_event = hg.lookup_table[current_event.parents.self_parent]

    return True


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
                x.confirmation_time = datetime.now().isoformat()
                # print("Decided for {}: round_received = {}, time = {}".format(x.short_id, x.round_received, x.consensus_time))
                decided_events.add(x)

    sorted_events = sorted(decided_events, key=lambda e: (e.round_received, e.consensus_time, e.id))
    for e in sorted_events:
        e.can_see_cache.clear()
        hg.unordered_events.remove(e.id)
        hg.ordered_events.append(e.id)


def get_consensus_time(hg, x) -> datetime:
    times = [dateutil.parser.parse(e.time) for e in get_events_for_consensus_time(hg, x)]
    timestamps = [int(time.mktime(t.timetuple())) for t in times]
    median_timestamp = int(median(timestamps)) if timestamps else 0
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

        # Go through the self ancestors
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
        else:  # Special case for the first event - this is not described in the paper
            result.add(z)

    return result
