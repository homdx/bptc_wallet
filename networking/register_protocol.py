from twisted.internet import protocol
from utilities.log_helper import logger
import json


class RegisterServerFactory(protocol.ServerFactory):

    def __init__(self, callback):
        self.callback = callback
        self.protocol = RegisterServer


class RegisterServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Client connected. Waiting for data...')

    def dataReceived(self, data):
        data_received = json.loads(data.decode('UTF-8'))
        member_id = data_received['member_id']
        port = data_received['port']
        info = self.transport.getPeer()
        self.factory.callback(member_id, port, info)

    def connectionLost(self, reason):
        logger.info('Client disconnected')


class RegisterClientFactory(protocol.ClientFactory):

    def __init__(self, member_id, port):
        self.member_id = member_id
        self.port = port
        self.protocol = RegisterClient


class RegisterClient(protocol.Protocol):

    def connectionMade(self):
        data_to_send = {'member_id': self.factory.member_id, 'port': self.factory.port}
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        logger.info('Disconnected')
