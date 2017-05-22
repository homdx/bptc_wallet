import logging
from networking import LocalNetwork


def run_network(n_nodes, n_turns):
    network = LocalNetwork(n_nodes)

    for i in range(n_turns):
        node = network.get_random_node()
        logging.info("working node: {}, event number: {}".format(node, i))
        node.heartbeat_callback()

    return network

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    run_network(4, 1000)
