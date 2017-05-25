from twisted.internet import protocol
import json
from utilities.log_helper import logger
from hashgraph.event import SerializableEvent, Event


class PushServerFactory(protocol.ServerFactory):

    def __init__(self, callback):
        self.callback = callback
        self.protocol = PushServer


class PushServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Client connected. Waiting for data...')

    def dataReceived(self, data):
        data_decoded = data.decode('UTF-8')
        s_events = json.loads(data_decoded)
        events = {}
        for event_id, s_event in s_events.items():
            events[event_id] = Event.create_from(s_event)
        logger.info('Received: {}'.format(events))
        self.factory.callback(events)

    def connectionLost(self, reason):
        logger.info('Client disconnected')


class PushClientFactory(protocol.ClientFactory):

    def __init__(self, events):
        self.events = events
        self.protocol = PushClient


class PushClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server.')
        logger.info('Sending: {}'.format(self.factory.events))
        # TODO: move somewhere else
        data_to_send = {}
        for event_id, event in self.factory.events.items():
            data_to_send[event_id] = SerializableEvent(event.data, event.parents,
                                                       event.height, event.time, str(event.verify_key))
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        logger.info('Disconnected')
