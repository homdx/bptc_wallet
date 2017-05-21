from twisted.internet import reactor, protocol
from utils.log_helper import logger


class Echo(protocol.Protocol):
    """This is just about the simplest possible protocol"""

    def connectionMade(self):
        logger.info('Connected to client')

    def dataReceived(self, data):
        """As soon as any data is received, write it back."""
        logger.info('Data received from client')
        self.transport.write(data)

    def connectionLost(self, reason):
        logger.info('Connection to client lost')


class EchoClient(protocol.Protocol):
    """Once connected, send a message, then print the result."""

    def connectionMade(self):
        logger.info('Connected to server')
        self.transport.write('Hello, world!'.encode('UTF-8'))

    def dataReceived(self, data):
        """As soon as any data is received, write it back."""
        logger.info('Data received from server')
        self.transport.loseConnection()

    def connectionLost(self, reason):
        logger.info('Connection to server lost')


class ClientFactory(protocol.ClientFactory):
    protocol = EchoClient

    def clientConnectionFailed(self, connector, reason):
        logger.info('Connection failed - goodbye!')

    def clientConnectionLost(self, connector, reason):
        logger.info('Connection lost - goodbye!')
