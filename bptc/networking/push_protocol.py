import json
from twisted.internet import protocol
from bptc.data.event import Event
from bptc.data.member import Member
import bptc.utils as utils
from typing import Dict, List


class PushServerFactory(protocol.ServerFactory):

    def __init__(self, receive_events_callback, receive_members_callback):
        self.receive_events_callback = receive_events_callback
        self.receive_members_callback = receive_members_callback
        self.protocol = PushServer


class PushServer(protocol.Protocol):

    def connectionMade(self):
        utils.logger.info('Client connected. Waiting for data...')

    def dataReceived(self, data):
        # Decode received JSON data
        received_data = json.loads(data.decode('UTF-8'))

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

            utils.logger.info('Received Events:')
            for event_id, event in events.items():
                utils.logger.info('{}'.format(event))

            self.factory.receive_events_callback(from_member, events)

        # Check if the sender sent any members
        s_members = received_data['members']
        if len(s_members) > 0:
            members = [Member.from_dict(m) for m in s_members]

            utils.logger.info('Received Members:')
            [utils.logger.info('{}'.format(m)) for m in members]

            self.factory.receive_members_callback(members)

    def connectionLost(self, reason):
        utils.logger.info('Client disconnected')


class PushClientFactory(protocol.ClientFactory):

    def __init__(self, from_member: Member, events: Dict[str, Event], members: List[Member]):
        self.from_member = from_member
        self.events = events
        self.members = members
        self.protocol = PushClient

    def clientConnectionLost(self, connector, reason):
        utils.logger.info('Lost connection.  Reason: {}'.format(reason))

    def clientConnectionFailed(self, connector, reason):
        utils.logger.info('Connection failed. Reason: {}'.format(reason))


class PushClient(protocol.Protocol):

    def connectionMade(self):
        utils.logger.info('Connected to server.')
        utils.logger.info('Sending:')
        for event_id, event in self.factory.events.items():
            utils.logger.info('{}'.format(event))

        serialized_events = {}
        if self.factory.events is not None:
            for event_id, event in self.factory.events.items():
                serialized_events[event_id] = event.to_dict()

        serialized_members = []
        if self.factory.members is not None:
            for member in self.factory.members:
                serialized_members.append(member.to_dict())

        data_to_send = {
            'from': {
                'verify_key': self.factory.from_member.verify_key,
                'listening_port': self.factory.from_member.address.port
            },
            'events': serialized_events,
            'members': serialized_members
        }

        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        utils.logger.info("Sent data")
        self.transport.loseConnection()

    def connectionLost(self, reason):
        utils.logger.info('Disconnected')
