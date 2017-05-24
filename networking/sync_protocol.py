from twisted.internet import protocol
import json
from utilities.log_helper import logger
from hashgraph.event import SerializableEvent, Event


class SyncServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to client. Waiting for data...')

    def dataReceived(self, data):
        logger.info('Data received and now sending data back ...')

        # TODO: move somewhere else?
        data_decoded = data.decode('UTF-8')
        s_events = json.loads(data_decoded)
        events = {}
        for event_id, s_event in s_events.items():
            events[event_id] = Event.create_from(s_event)

        self.factory.callback(events)

        # TODO: move somewhere else?
        data_to_send = {}
        for event_id, event in self.factory.member.hashgraph.lookup_table.items():
            data_to_send[event_id] = SerializableEvent(event.data, event.parents, event.height, event.time.isoformat(), str(event.verify_key))

        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))

    def connectionLost(self, reason):
        logger.info('Connection to client lost')


class SyncClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server. Sending and receiving data...')
        # TODO: move somewhere else
        data_to_send = {}
        for event_id, event in self.factory.member.hashgraph.lookup_table.items():
            data_to_send[event_id] = SerializableEvent(event.data, event.parents, event.height, event.time.isoformat(), str(event.verify_key))
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))

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


class SyncClientFactory(protocol.ClientFactory):

    def __init__(self, member):
        self.member = member
        self.callback = member.received_data_callback
        self.protocol = SyncClient


class SyncServerFactory(protocol.ServerFactory):

    def __init__(self, member):
        self.member = member
        self.callback = member.received_data_callback
        self.protocol = SyncServer
