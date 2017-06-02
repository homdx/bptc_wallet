from twisted.internet import protocol
import json
from utilities.log_helper import logger
from hptaler.data.event import SerializableEvent, Event
from hptaler.data.member import Member
from nacl.encoding import Base64Encoder


class PushServerFactory(protocol.ServerFactory):

    def __init__(self, callback):
        self.callback = callback
        self.protocol = PushServer


class PushServer(protocol.Protocol):

    def connectionMade(self):
        logger.info('Client connected. Waiting for data...')

    def dataReceived(self, data):
        # Decode received JSON data
        received_data = json.loads(data.decode('UTF-8'))

        # Generate Member object
        from_member_id = received_data['from']
        from_member = Member.from_string_verifykey(from_member_id)
        from_member.address = self.transport.getPeer()

        s_events = received_data['events']
        events = {}
        for event_id, s_event in s_events.items():
            events[event_id] = Event.from_serializable_event(s_event)

        logger.info('Received:')
        for event_id, event in events.items():
            logger.info('{}'.format(event))

        self.factory.callback(from_member, events)

    def connectionLost(self, reason):
        logger.info('Client disconnected')


class PushClientFactory(protocol.ClientFactory):

    def __init__(self, from_member: Member, events):
        self.from_member = from_member
        self.events = events
        self.protocol = PushClient


class PushClient(protocol.Protocol):

    def connectionMade(self):
        logger.info('Connected to server.')
        logger.info('Sending:')
        for event_id, event in self.factory.events.items():
            logger.info('{}'.format(event))

        serialized_events = {}
        for event_id, event in self.factory.events.items():
            serialized_events[event_id] = event.to_serializable_event()
        data_to_send = {
            'from': self.factory.from_member.verify_key.encode(encoder=Base64Encoder).decode("utf-8"),
            'events': serialized_events
        }
        self.transport.write(json.dumps(data_to_send).encode('UTF-8'))
        logger.info("Sent data")
        self.transport.loseConnection()

    def connectionLost(self, reason):
        logger.info('Disconnected')
