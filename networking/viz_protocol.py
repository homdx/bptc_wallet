from twisted.internet import protocol
import json
from utilities.log_helper import logger
from hashgraph.event import Event


class VizClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server')

    def dataReceived(self, data):
        logger.info('Data received')
        data_decoded = data.decode('UTF-8')
        s_events = json.loads(data_decoded)
        lookup_table = {}
        for event_id, s_event in s_events.items():
            lookup_table[event_id] = Event.create_from(s_event)
        self.factory.callback(lookup_table)

    def connectionLost(self, reason):
        logger.info('Connection to server lost')


class VizClientFactory(protocol.ClientFactory):

    def __init__(self, callback):
        self.callback = callback
        self.protocol = VizClient
