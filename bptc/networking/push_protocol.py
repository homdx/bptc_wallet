import json
import zlib
from twisted.internet import protocol
import bptc
from bptc.data.event import Event
from bptc.data.member import Member
from typing import Dict, List
import threading
from builtins import UnicodeDecodeError

network_lock = threading.Lock()


class PushServerFactory(protocol.ServerFactory):

    def __init__(self, receive_events_callback, receive_members_callback):
        self.receive_events_callback = receive_events_callback
        self.receive_members_callback = receive_members_callback
        self.protocol = PushServer


class PushServer(protocol.Protocol):

    def connectionMade(self):
        self.transport.setTcpNoDelay(True)
        bptc.logger.info('Client connected. Waiting for data...')

    def dataReceived(self, data):
        with network_lock:
            try:
                data = zlib.decompress(data)
            except zlib.error as err:
                bptc.logger.error(err)

            # Decode received JSON data
            try:
                received_data = json.loads(data.decode('UTF-8'))
            except (json.decoder.JSONDecodeError, UnicodeDecodeError) as err:
                bptc.logger.error(err)
                bptc.logger.error(data.decode('UTF-8'))

            # Generate Member object
            from_member_id = received_data['from']['verify_key']
            from_member_port = int(received_data['from']['listening_port'])
            from_member = Member(from_member_id, None)
            from_member.address = self.transport.getPeer()
            from_member.address.port = from_member_port

            # Check if the sender sent any events
            s_events = received_data['events']
            if len(s_events) > 0:
                events = {}
                for event_id, dict_event in s_events.items():
                    events[event_id] = Event.from_dict(dict_event)

                bptc.logger.info('- Received {} events'.format(len(events.items())))

                self.factory.receive_events_callback(from_member, events)

            # Check if the sender sent any members
            s_members = received_data['members']
            if len(s_members) > 0:
                members = [Member.from_dict(m) for m in s_members]

                bptc.logger.info('- Received {} members'.format(len(members)))

                self.factory.receive_members_callback(members)

    def connectionLost(self, reason):
        bptc.logger.info('Client disconnected')


class PushClientFactory(protocol.ClientFactory):

    def __init__(self, string_to_send):
        self.string_to_send = string_to_send
        self.protocol = PushClient

    def clientConnectionLost(self, connector, reason):
        return

    def clientConnectionFailed(self, connector, reason):
        bptc.logger.info('Connection failed. Reason: {}'.format(reason))


class PushClient(protocol.Protocol):

    def connectionMade(self):
        with network_lock:
            bptc.logger.info('Connected to server.')
            # bptc.logger.info('- Sending {} events'.format(len(self.factory.events.items())))
            # bptc.logger.info('- Sending {} members'.format(len(self.factory.members)))
            self.transport.write(zlib.compress(self.factory.string_to_send))
            bptc.logger.info("- Sent data")
            self.transport.loseConnection()

    def connectionLost(self, reason):
        bptc.logger.info('Disconnected')
