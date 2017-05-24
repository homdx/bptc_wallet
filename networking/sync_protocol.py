from twisted.internet import protocol
from utilities.log_helper import logger


class SyncServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to client. Waiting for data...')

    def dataReceived(self, data):
        data = data.decode('UTF-8')
        #logger.info('Received: {}'.format(data))
        self.factory.callback(data)

    def connectionLost(self, reason):
        logger.info('Connection to client lost')


class SyncClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server. Sending data...')
        self.transport.write(self.factory.data.encode('UTF-8'))

    def connectionLost(self, reason):
        logger.info('Connection to server lost')


class SyncClientFactory(protocol.ClientFactory):

    def __init__(self, data):
        self.protocol = SyncClient
        self.data = data


class SyncServerFactory(protocol.ServerFactory):

    def __init__(self, callback):
        self.protocol = SyncServer
        self.callback = callback
