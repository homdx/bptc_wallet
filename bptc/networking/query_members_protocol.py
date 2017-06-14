import json
from twisted.internet import protocol


class QueryMembersServerFactory(protocol.ServerFactory):

    def __init__(self, members):
        self.members = members
        self.protocol = QueryMembersServer


class QueryMembersServer(protocol.Protocol):

    def connectionMade(self):
        self.transport.write(json.dumps(self.factory.members).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        return


class QueryMembersClientFactory(protocol.ClientFactory):

    def __init__(self, callback_obj, callback):
        self.callback_obj = callback_obj
        self.callback = callback
        self.protocol = QueryMembersClient


class QueryMembersClient(protocol.Protocol):

    def connectionMade(self):
        return

    def dataReceived(self, data):
        data_received = json.loads(data.decode('UTF-8'))
        self.factory.callback(data_received)

    def connectionLost(self, reason):
        return
