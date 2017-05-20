from twisted.internet import reactor, protocol


class Echo(protocol.Protocol):
    """This is just about the simplest possible protocol"""

    def dataReceived(self, data):
        """As soon as any data is received, write it back."""
        self.transport.write(data)


class EchoClient(protocol.Protocol):
    """Once connected, send a message, then print the result."""

    def connectionMade(self):
        self.transport.write('hello, world!'.encode('UTF-8'))

    def dataReceived(self, data):
        """As soon as any data is received, write it back."""
        print('Server said:', data)
        self.transport.loseConnection()

    def connectionLost(self, reason):
        print('connection lost')


class ClientFactory(protocol.ClientFactory):
    protocol = EchoClient

    def clientConnectionFailed(self, connector, reason):
        print('Connection failed - goodbye!')
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print('Connection lost - goodbye!')
        reactor.stop()

