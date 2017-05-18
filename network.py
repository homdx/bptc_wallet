from utils import randrange
from node import Node


class LocalNetwork(object):

    def __init__(self, n_nodes):
        """Creates local network with given number of nodes."""
        self.size = n_nodes
        nodes = [Node.create() for i in range(n_nodes)]
        stake = {node.id: 1 for node in nodes}
        for node in nodes:
            node.set(stake)  # TODO make network creation explicit !

        self.nodes = nodes
        for node in self.nodes:
            for other_node in self.nodes:
                if node != other_node:
                    node.acquaint(other_node)

        self.ids = {node.id: i for i, node in enumerate(nodes)}

        self.heartbeat_callbacks = [n.heartbeat_callback for n in self.nodes]

    def get_random_node(self):
        i = randrange(self.size)
        return self.nodes[i]