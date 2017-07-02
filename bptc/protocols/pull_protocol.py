import json
import zlib
from twisted.internet import protocol
from functools import partial
import bptc
from bptc.data.event import Event


class PullServerFactory(protocol.ServerFactory):

    def __init__(self, me_id, hashgraph):
        self.me_id = me_id
        self.hashgraph = hashgraph
        self.protocol = PullServer


class PullServer(protocol.Protocol):

    def connectionMade(self):
        serialized_events = {}
        with self.factory.hashgraph.lock:
            for event_id, event in self.factory.hashgraph.lookup_table.items():
                serialized_events[event_id] = event.to_dict()

        data_string = {'from': self.factory.me_id, 'events': serialized_events}
        data_to_send = zlib.compress(json.dumps(data_string).encode('UTF-8'))
        if len(data_to_send) > 65536:
            raise AssertionError('Twisted only allows 65536 Bytes to be sent this way! Data to send is {} Bytes'.
                                 format(len(data_to_send)))
        self.transport.write(data_to_send)
        self.transport.loseConnection()

    def connectionLost(self, reason):
        return


class PullClientFactory(protocol.ClientFactory):

    def __init__(self, callback_obj, doc):
        self.callback_obj = callback_obj
        self.doc = doc
        self.protocol = PullClient

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        bptc.logger.info('Connection failed. Reason: {}'.format(reason))


class PullClient(protocol.Protocol):

    def connectionMade(self):
        return

    def dataReceived(self, data):
        print(len(data))
        try:
            data = zlib.decompress(data)
        except zlib.error as err:
            raise AssertionError(err)

        received_data = json.loads(data.decode('UTF-8'))
        from_member = received_data['from']
        s_events = received_data['events']
        events = {}
        for event_id, dict_event in s_events.items():
            events[event_id] = Event.from_dict(dict_event)

        self.factory.doc.add_next_tick_callback(
            partial(self.factory.callback_obj.received_data_callback, from_member, events))
        self.factory.doc.add_next_tick_callback(self.factory.callback_obj.draw)

    def connectionLost(self, reason):
        return
