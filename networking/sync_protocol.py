from twisted.internet import protocol
from utilities.log_helper import logger


class SyncServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to client')

    def dataReceived(self, data):
        logger.info('Received: {}'.format(data))

    def connectionLost(self, reason):
        logger.info('Connection to client lost')


class SyncClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server. Sending hashgraph...')
        self.transport.write(self.factory.data.encode('UTF-8'))

    def connectionLost(self, reason):
        logger.info('Connection to server lost')


class SyncClientFactory(protocol.ClientFactory):

    def __init__(self, data):
        self.protocol = SyncClient
        self.data = data

    def clientConnectionFailed(self, connector, reason):
        logger.info('Connection failed - goodbye!')

    def clientConnectionLost(self, connector, reason):
        logger.info('Connection lost - goodbye!')
