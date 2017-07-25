import json
from twisted.internet import protocol

import bptc

"""The register protocol is used between a client and a member registry for the registration."""


class RegisterServerFactory(protocol.ServerFactory):

    def __init__(self, callback):
        self.callback = callback
        self.protocol = RegisterServer


class RegisterServer(protocol.Protocol):
    """The register server handles the registration of the register clients."""

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        return

    def dataReceived(self, data):
        try:
            data_received = json.loads(data.decode('UTF-8'))
        except:
            bptc.logger.warn("Could not parse JSON message")
            return

        member_id = data_received['member_id']
        port = data_received['port']
        info = self.transport.getPeer()
        self.factory.callback(member_id, port, info)

    def connectionLost(self, reason):
        return


class RegisterClientFactory(protocol.ClientFactory):

    def __init__(self, member_id, port):
        self.member_id = member_id
        self.port = port
        self.protocol = RegisterClient

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        # Debug logging level because this might happen very often and is an
        # expected behaviour within our framework
        bptc.logger.debug('Connection failed. Reason: {}'.format(reason))


class RegisterClient(protocol.Protocol):
    """The register client registers at a register server."""

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        data_to_send = {'member_id': self.factory.member_id, 'port': self.factory.port}
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        return
