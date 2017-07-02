import zlib
from twisted.internet import protocol
import bptc


class PushServerFactory(protocol.ServerFactory):

    def __init__(self, receive_data_string_callback):
        self.receive_data_string_callback = receive_data_string_callback
        self.protocol = PushServer


class PushServer(protocol.Protocol):

    def connectionMade(self):
        # bptc.logger.info('Client connected. Waiting for data...')
        pass

    def dataReceived(self, data):
        try:
            data = zlib.decompress(data)
        except zlib.error as err:
            bptc.logger.error(err)

        self.factory.receive_data_string_callback(data.decode('UTF-8'), self.transport.getPeer())

    def connectionLost(self, reason):
        # bptc.logger.info('Client disconnected')
        pass


class PushClientFactory(protocol.ClientFactory):

    def __init__(self, string_to_send):
        self.string_to_send = string_to_send
        self.protocol = PushClient

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        # bptc.logger.info('Connection failed. Reason: {}'.format(reason))
        pass


class PushClient(protocol.Protocol):

    def connectionMade(self):
        # bptc.logger.info('Connected to server.')
        # bptc.logger.info('- Sending {} events'.format(len(self.factory.events.items())))
        # bptc.logger.info('- Sending {} members'.format(len(self.factory.members)))
        self.transport.write(zlib.compress(self.factory.string_to_send))
        # bptc.logger.info("- Sent data")
        self.transport.loseConnection()

    def connectionLost(self, reason):
        # bptc.logger.info('Disconnected')
        pass
