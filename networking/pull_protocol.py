from twisted.internet import protocol
import json
from utilities.log_helper import logger
from hashgraph.event import SerializableEvent, Event


class PullServerFactory(protocol.ServerFactory):

    def __init__(self, member):
        self.member = member
        self.protocol = PullServer


class PullServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Client connected')
        logger.info('Sending:')
        for event_id, event in self.factory.member.hashgraph.lookup_table.items():
            logger.info('{}'.format(event))

        # TODO: move somewhere else
        data_to_send = {}
        for event_id, event in self.factory.member.hashgraph.lookup_table.items():
            data_to_send[event_id] = SerializableEvent(event.data, event.parents,
                                                       event.height, event.time, str(event.verify_key))
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        logger.info('Client disconnected')


class PullClientFactory(protocol.ClientFactory):

    def __init__(self, callback_obj, callback):
        self.callback_obj = callback_obj
        self.callback = callback
        self.protocol = PullClient


class PullClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server. Waiting for data...')

    def dataReceived(self, data):
        # TODO: move somewhere else?
        data_decoded = data.decode('UTF-8')
        s_events = json.loads(data_decoded)
        events = {}
        for event_id, s_event in s_events.items():
            events[event_id] = Event.create_from(s_event)

        logger.info('Received:')
        for event_id, event in events.items():
            logger.info('{}'.format(event))

        self.factory.callback(self.factory.callback_obj, events)

    def connectionLost(self, reason):
        logger.info('Disconnected')
