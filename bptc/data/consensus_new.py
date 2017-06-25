C = 6  # How often a coin round occurs, e.g. 6 for every sixth round


def divide_rounds(hashgraph, events):
    for event in events:
        r = 1
        print(event)
        if event.parents.self_parent is not None:
            r = hashgraph.lookup_table[event.parents.self_parent].round
        if event.parents.other_parent is not None:
            r = max(r, hashgraph.lookup_table[event.parents.other_parent].round)
        if hashgraph.can_stongly_see_enough_round_r_witnesses(event):
            event.round = r + 1
        else:
            event.round = r
        event.witness = event.parents.self_parent is None or event.round > hashgraph.lookup_table[event.parents.self_parent].round


def decide_fame(hashgraph):
    pass


def find_order(self, new_c):
    pass
