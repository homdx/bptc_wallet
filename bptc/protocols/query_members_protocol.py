import json
from twisted.internet import protocol
import bptc

"""The query members protocol is used between a client and a member registry for querying the members."""


class QueryMembersServerFactory(protocol.ServerFactory):

    def __init__(self, members):
        self.members = members
        self.protocol = QueryMembersServer


class QueryMembersServer(protocol.Protocol):
    """The query members server handles the query of a query members client"""

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        self.transport.write(json.dumps(self.factory.members).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        return


class QueryMembersClientFactory(protocol.ClientFactory):

    def __init__(self, callback_obj, callback):
        self.callback_obj = callback_obj
        self.callback = callback
        self.protocol = QueryMembersClient

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        # Debug logging level because this might happen very often and is an
        # expected behaviour within our framework
        bptc.logger.debug('Connection failed. Reason: {}'.format(reason))


class QueryMembersClient(protocol.Protocol):
    """The query member client queries the members of a query members server."""

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        return

    def dataReceived(self, data):
        try:
            data_received = json.loads(data.decode('UTF-8'))
        except:
            bptc.logger.warn("Could not parse JSON message")
            return

        self.factory.callback(data_received)

    def connectionLost(self, reason):
        return
