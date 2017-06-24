import json
from twisted.internet import protocol
import bptc


class QueryMembersServerFactory(protocol.ServerFactory):

    def __init__(self, members):
        self.members = members
        self.protocol = QueryMembersServer


class QueryMembersServer(protocol.Protocol):

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
        #bptc.logger.info('Lost connection.  Reason: {}'.format(reason))
        return

    def clientConnectionFailed(self, connector, reason):
        bptc.logger.info('Connection failed. Reason: {}'.format(reason))


class QueryMembersClient(protocol.Protocol):

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        return

    def dataReceived(self, data):
        data_received = json.loads(data.decode('UTF-8'))
        self.factory.callback(data_received)

    def connectionLost(self, reason):
        return
