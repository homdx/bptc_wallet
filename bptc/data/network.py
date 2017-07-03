import queue
from random import choice
from typing import Dict, List
from twisted.internet import threads, reactor
import json
import bptc
from bptc.data.event import Event, Parents
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member
from bptc.data.transaction import MoneyTransaction, PublishNameTransaction
from bptc.protocols.push_protocol import PushClientFactory
import time
import threading


class Network:

    def __init__(self, hashgraph: Hashgraph, create_initial_event: bool = True):
        # The current hashgraph
        self.hashgraph = hashgraph
        self.me = self.hashgraph.me
        self.background_push_client_thread = None

        self.background_push_server_thread = PushingServerThread(self)
        self.background_push_server_thread.daemon = True
        self.background_push_server_thread.start()

        # Create first own event
        if create_initial_event:
            self.hashgraph.add_own_event(Event(self.hashgraph.me.verify_key, None, Parents(None, None)))

    def push_to(self, ip, port) -> None:
        """Update hg and return new event ids in topological order."""
        data_string = self.generate_data_string(self.hashgraph.me,
                                                self.hashgraph.lookup_table,
                                                filter_members_with_address(self.hashgraph.known_members.values()))
        factory = PushClientFactory(data_string)

        def push():
            reactor.connectTCP(ip, port, factory)

        threads.blockingCallFromThread(reactor, push)

        return

    @staticmethod
    def generate_data_string(me, events, members):
        serialized_events = {}
        if events is not None:
            for event_id, event in events.items():
                serialized_events[event_id] = event.to_dict()

        serialized_members = []
        if members is not None:
            for member in members:
                serialized_members.append(member.to_dict())

        data_to_send = {
            'from': {
                'verify_key': me.verify_key,
                'listening_port': me.address.port
            },
            'events': serialized_events,
            'members': serialized_members
        }

        return json.dumps(data_to_send).encode('UTF-8')

    def push_to_member(self, member: Member) -> None:
        bptc.logger.debug('Push to {}... ({}, {})'.format(member.verify_key[:6], member.address.host, member.address.port))

        data_string = self.generate_data_string(self.hashgraph.me,
                                                self.hashgraph.get_unknown_events_of(member),
                                                filter_members_with_address(self.hashgraph.known_members.values()))
        factory = PushClientFactory(data_string)

        def push():
            reactor.connectTCP(member.address.host, member.address.port, factory)

        threads.blockingCallFromThread(reactor, push)

    def push_to_random(self) -> None:
        """
        Pushes to a random, known member
        :return: None
        """
        filtered_known_members = dict(self.hashgraph.known_members)
        filtered_known_members.pop(self.hashgraph.me.verify_key, None)
        if filtered_known_members:
            _, member = choice(list(filtered_known_members.items()))
            self.push_to_member(member)
        else:
            bptc.logger.debug("Don't know any other members. Get them from the registry!")

    def send_transaction(self, amount: int, comment: str, receiver: Member) -> Event:
        """
        Create a new event with a transaction
        :param amount: The amount of BBTC to send
        :param comment: The comment to be included in the transaction
        :param receiver: The receiver of the transaction
        :return:
        """
        transaction = MoneyTransaction(receiver.to_verifykey_string(), amount, comment)
        event = Event(self.hashgraph.me.verify_key, [transaction], Parents(self.hashgraph.me.head, None))
        self.hashgraph.add_own_event(event)
        return event

    def publish_name(self, name: str):
        """
        Publishes a user's name on the hashgraph
        :param name: The user's name
        :return:
        """
        transaction = PublishNameTransaction(name)
        event = Event(self.hashgraph.me.verify_key, [transaction], Parents(self.hashgraph.me.head, None))
        self.hashgraph.add_own_event(event)
        return event

    def receive_data_string_callback(self, data_string, peer):
        self.background_push_server_thread.q.put((data_string, peer))

    def process_data_string(self, data_string, peer):
        # Decode received JSON data
        received_data = json.loads(data_string)

        # Generate Member object
        from_member_id = received_data['from']['verify_key']
        from_member_port = int(received_data['from']['listening_port'])
        from_member = Member(from_member_id, None)
        from_member.address = peer
        from_member.address.port = from_member_port

        # Check if the sender sent any events
        s_events = received_data['events']
        if len(s_events) > 0:
            events = {}
            for event_id, dict_event in s_events.items():
                events[event_id] = Event.from_dict(dict_event)

            bptc.logger.info('- Received {} events'.format(len(events.items())))

            self.process_events(from_member, events)

        # Check if the sender sent any members
        s_members = received_data['members']
        if len(s_members) > 0:
            members = [Member.from_dict(m) for m in s_members]

            bptc.logger.info('- Received {} members'.format(len(members)))

            self.receive_members_callback(members)

    def process_events(self, from_member: Member, events: Dict[str, Event]) -> None:
        """
        Used as a callback when events are received from the outside
        :param from_member: The member from which the events were received
        :param events: The list of events
        :return: None
        """
        # Store/Update member
        if from_member.id in self.hashgraph.known_members:
            self.hashgraph.known_members[from_member.id].address = from_member.address
        else:
            self.hashgraph.known_members[from_member.id] = from_member

        # Let the hashgraph process the events
        self.hashgraph.process_events(from_member, events)

    def receive_members_callback(self, members: List[Member]) -> None:
        """
        Used as a callback when member are received from the outside
        :param members: The ist of members
        :return: None
        """
        for member in members:
            if member.id not in self.hashgraph.known_members:
                self.hashgraph.known_members[member.id] = member
            elif self.hashgraph.known_members[member.id].address is None:
                self.hashgraph.known_members[member.id].address = member.address

    def start_background_pushes(self) -> None:
        self.background_push_client_thread = PushingClientThread(self)
        self.background_push_client_thread.daemon = True
        self.background_push_client_thread.start()

    def stop_background_pushes(self) -> None:
        self.background_push_client_thread.stop()


def filter_members_with_address(members: List[Member]) -> List[Member]:
    """
    Filters a list of members, only returning those who have a known network address
    :param members: The list of members to be filtered
    :return: The filtered lise
    """
    return [m for m in members if m.address is not None]


class PushingClientThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, network):
        super(PushingClientThread, self).__init__()
        self.network = network
        self._stop_event = threading.Event()

    def run(self):
        while not self.stopped():
            with self.network.hashgraph.lock:
                self.network.push_to_random()
            bptc.logger.debug("Performed automatic push to random at {}".format(time.ctime()))
            time.sleep(1)

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class PushingServerThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, network):
        super(PushingServerThread, self).__init__()
        self.network = network
        self._stop_event = threading.Event()
        self.q = queue.Queue()

    def run(self):
        while not self.stopped():
            (data_string, peer) = self.q.get()
            with self.network.hashgraph.lock:
                self.network.process_data_string(data_string, peer)
            self.q.task_done()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()
