from twisted.internet import protocol
import json
from utilities.log_helper import logger
from hptaler.data.event import SerializableEvent, Event


class PullServerFactory(protocol.ServerFactory):

    def __init__(self, member):
        self.from_member = member
        self.protocol = PullServer


class PullServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Client connected')
        logger.info('Sending:')
        for event_id, event in self.factory.from_member.hashgraph.lookup_table.items():
            logger.info('{}'.format(event))

        serialized_events = {}
        for event_id, event in self.factory.from_member.hashgraph.lookup_table.items():
            serialized_events[event_id] = SerializableEvent(event.data, event.parents,
                                                       event.height, event.time, str(event.verify_key))
        data_to_send = {'from': str(self.factory.from_member.id), 'events': serialized_events}
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
        received_data = json.loads(data.decode('UTF-8'))
        from_member = received_data['from']
        s_events = received_data['events']
        events = {}
        for event_id, s_event in s_events.items():
            events[event_id] = Event.create_from(s_event)

        logger.info('Received:')
        for event_id, event in events.items():
            logger.info('{}'.format(event))

        self.factory.callback(self.factory.callback_obj, from_member, events)

    def connectionLost(self, reason):
        logger.info('Disconnected')
