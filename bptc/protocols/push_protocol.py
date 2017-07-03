import zlib

from math import ceil
from twisted.internet import protocol
import bptc


class PushServerFactory(protocol.ServerFactory):

    def __init__(self, receive_data_string_callback):
        self.receive_data_string_callback = receive_data_string_callback
        self.protocol = PushServer
        self.received_data = b""


class PushServer(protocol.Protocol):

    def connectionMade(self):
        self.transport.write('I\'m alive!'.encode('UTF-8'))

    def dataReceived(self, data):
        self.factory.received_data += data
        self.transport.loseConnection()

    def connectionLost(self, reason):
        if len(self.factory.received_data) == 0:
            bptc.logger.warn('No data received!')
            return
        if self.factory.received_data[:3] == b'GET':
            # Request is an HTTP request
            return
        try:
            data = zlib.decompress(self.factory.received_data)
            self.factory.receive_data_string_callback(data.decode('UTF-8'), self.transport.getPeer())
        except zlib.error as err:
            bptc.logger.error(
                'Failed parsing input: {} \n\n Error message: {}'.format(
                    self.factory.received_data, err))


class PushClientFactory(protocol.ClientFactory):

    def __init__(self, string_to_send):
        self.string_to_send = string_to_send
        self.protocol = PushClient

    def clientConnectionLost(self, connector, reason):
        if reason.getErrorMessage() != 'Connection was closed cleanly.':
            bptc.logger.error("ConnLost: {}".format(reason.getErrorMessage()))
        return

    def clientConnectionFailed(self, connector, reason):
        if reason.getErrorMessage() != 'Connection was closed cleanly.':
            bptc.logger.error("ConnFailed: {}".format(reason.getErrorMessage()))
        pass


class PushClient(protocol.Protocol):

    def connectionMade(self):
        data_to_send = zlib.compress(self.factory.string_to_send)
        for i in range(1, (ceil(len(data_to_send) / 65536)) + 1):
            self.transport.write(data_to_send[(i-1) * 65536:min(i*65536, len(data_to_send))])
        self.transport.loseConnection()

    def connectionLost(self, reason):
        pass
