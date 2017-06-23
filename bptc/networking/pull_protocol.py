import json
from twisted.internet import protocol
from functools import partial
from bptc.data.event import Event
from bptc.data.network import Network
import bptc.utils as utils


class PullServerFactory(protocol.ServerFactory):

    def __init__(self, network: Network):
        self.network = network
        self.protocol = PullServer


class PullServer(protocol.Protocol):

    def connectionMade(self):
        #utils.logger.info('Client connected')

        serialized_events = {}
        for event_id, event in self.factory.network.hashgraph.lookup_table.items():
            serialized_events[event_id] = event.to_debug_dict()

        data_to_send = {'from': str(self.factory.network.me.id), 'events': serialized_events}
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        self.transport.loseConnection()

    def connectionLost(self, reason):
        #utils.logger.info('Client disconnected')
        return


class PullClientFactory(protocol.ClientFactory):

    def __init__(self, callback_obj, doc):
        self.callback_obj = callback_obj
        self.doc = doc
        self.protocol = PullClient

    def clientConnectionLost(self, connector, reason):
        #utils.logger.info('Lost connection.  Reason: {}'.format(reason))
        return

    def clientConnectionFailed(self, connector, reason):
        utils.logger.info('Connection failed. Reason: {}'.format(reason))


class PullClient(protocol.Protocol):

    def connectionMade(self):
        #utils.logger.info('Connected to server. Waiting for data...')
        return

    def dataReceived(self, data):
        received_data = json.loads(data.decode('UTF-8'))
        from_member = received_data['from']
        s_events = received_data['events']
        events = {}
        for event_id, dict_event in s_events.items():
            events[event_id] = Event.from_debug_dict(dict_event)

        self.factory.doc.add_next_tick_callback(
            partial(self.factory.callback_obj.received_data_callback, from_member, events))
        self.factory.doc.add_next_tick_callback(self.factory.callback_obj.draw)

    def connectionLost(self, reason):
        #utils.logger.info('Disconnected')
        return