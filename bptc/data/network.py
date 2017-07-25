import queue
from random import choice
from typing import Dict, List
import random
import json
from bptc.data.event import Event, Parents
from bptc.data.hashgraph import Hashgraph
from bptc.data.transaction import MoneyTransaction, PublishNameTransaction
from bptc.data.db import DB
from bptc.protocols.push_protocol import PushClientFactory
import time
from datetime import datetime
import threading
from functools import partial
from twisted.internet import reactor, threads
from twisted.internet.address import IPv4Address
import bptc
from bptc.data.member import Member
from bptc.protocols.push_protocol import PushServerFactory
from bptc.protocols.query_members_protocol import QueryMembersClientFactory
from bptc.protocols.register_protocol import RegisterClientFactory
from bptc.protocols.pull_protocol import PullServerFactory


class Network:

    def __init__(self, hashgraph: Hashgraph, create_initial_event: bool = True):
        # The current hashgraph
        self.hashgraph = hashgraph
        self.background_push_client_thread = None

        self.background_push_server_thread = PushingServerThread(self)
        self.background_push_server_thread.daemon = True
        self.background_push_server_thread.start()

        # Statistics
        self.last_push_sent = None
        self.last_push_received = None

        # Create first own event
        if create_initial_event:
            self.hashgraph.add_own_event(Event(self.hashgraph.me.verify_key, None, Parents(None, None)), True)

    @property
    def me(self):
        return self.hashgraph.me

    def reset(self):
        DB.reset()
        new_me = Member.create()
        new_me.address = IPv4Address("TCP", bptc.ip, bptc.port)
        new_hashgraph = Hashgraph(new_me)
        self.hashgraph = new_hashgraph
        self.hashgraph.add_own_event(Event(self.hashgraph.me.verify_key, None, Parents(None, None)), True)
        self.last_push_sent = None
        self.last_push_received = None

    def push_to(self, ip, port) -> None:
        with self.hashgraph.lock:
            data_string = self.generate_data_string(self.hashgraph.me,
                                                    self.hashgraph.lookup_table,
                                                    filter_members_with_address(self.hashgraph.known_members.values()))

        factory = PushClientFactory(data_string, network=self)

        def push():
            reactor.connectTCP(ip, port, factory)

        threads.blockingCallFromThread(reactor, push)

    @staticmethod
    def generate_data_string(me, events, members):
        serialized_events = {}
        if events is not None:
            for event_id, event in events.items():
                serialized_events[event_id] = event.to_dict()

        serialized_members = []
        if members is not None:
            for member in members:
                if member.id is not me.verify_key:
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

    def push_to_member(self, member: Member, ignore_for_statistics=False) -> None:
        bptc.logger.debug('Push to {}... ({}, {})'.format(member.verify_key[:6], member.address.host, member.address.port))

        with self.hashgraph.lock:
            data_string = self.generate_data_string(self.hashgraph.me,
                                                    self.hashgraph.get_unknown_events_of(member),
                                                    filter_members_with_address(self.hashgraph.known_members.values()))

        if not ignore_for_statistics:
            factory = PushClientFactory(data_string, network=self, receiver=member)
        else:
            factory = PushClientFactory(data_string, network=None, receiver=member)

        def push():
            if member.address is not None:
                reactor.connectTCP(member.address.host, member.address.port, factory)

        threads.blockingCallFromThread(reactor, push)

    def push_to_random(self) -> None:
        """
        Pushes to a random, known member
        :return: None
        """
        with self.hashgraph.lock:
            filtered_known_members = [m for key, m in self.hashgraph.known_members.items()
                                      if key != self.hashgraph.me.verify_key
                                      and m.address is not None
                                      and key not in self.hashgraph.fork_blacklist]

        if filtered_known_members:
            member = choice(filtered_known_members)
            self.push_to_member(member)
        else:
            bptc.logger.debug("I don't know any other members!")

    def send_transaction(self, amount: int, comment: str, receiver: Member) -> Event:
        """
        Create a new event with a transaction
        :param amount: The amount of BBTC to send
        :param comment: The comment to be included in the transaction
        :param receiver: The receiver of the transaction
        :return:
        """
        transaction = MoneyTransaction(receiver.to_verifykey_string(), amount, comment)

        with self.hashgraph.lock:
            event = Event(self.hashgraph.me.verify_key, [transaction], Parents(self.hashgraph.me.head, None))
            self.hashgraph.add_own_event(event, True)

        return event

    def publish_name(self, name: str):
        """
        Publishes a user's name on the hashgraph
        :param name: The user's name
        :return:
        """
        transaction = PublishNameTransaction(name)

        with self.hashgraph.lock:
            event = Event(self.hashgraph.me.verify_key, [transaction], Parents(self.hashgraph.me.head, None))
            self.hashgraph.add_own_event(event, True)

        return event

    def receive_data_string_callback(self, data_string, peer):
        try:
            self.background_push_server_thread.q.put((data_string, peer), block=False)
        except:
            pass

    def process_data_string(self, data_string, peer):
        # Decode received JSON data
        try:
            received_data = json.loads(data_string)
        except:
            bptc.logger.warn("Could not parse JSON message")
            return

        # Ignore pushes from yourself (should only happen once after the client is started)
        if received_data['from']['verify_key'] == self.me.verify_key:
            return

        # Log
        self.last_push_received = datetime.now().isoformat()

        # Generate Member object
        from_member_id = received_data['from']['verify_key']
        from_member_listening_port = int(received_data['from']['listening_port'])
        from_member = Member(from_member_id, None)
        from_member.address = peer
        from_member.address.port = from_member_listening_port

        # Check if the sender sent any events
        s_events = received_data['events']
        if len(s_events) > 0:
            events = {}
            for event_id, dict_event in s_events.items():
                events[event_id] = Event.from_dict(dict_event)

            bptc.logger.debug('- Received {} events'.format(len(events.items())))

            self.process_events(from_member, events)

        # Check if the sender sent any members
        s_members = received_data['members']
        if len(s_members) > 0:
            members = [Member.from_dict(m) for m in s_members]

            bptc.logger.debug('- Received {} members'.format(len(members)))

            self.receive_members_callback(members)

    def process_events(self, from_member: Member, events: Dict[str, Event]) -> None:
        """
        Used as a callback when events are received from the outside
        :param from_member: The member from which the events were received
        :param events: The list of events
        :return: None
        """
        # Store/Update member
        with self.hashgraph.lock:
            if from_member.id in self.hashgraph.known_members:
                self.hashgraph.known_members[from_member.id].address = from_member.address
                from_member = self.hashgraph.known_members[from_member.id]
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
        with self.hashgraph.lock:
            for member in members:
                if member.id not in self.hashgraph.known_members:
                    self.hashgraph.known_members[member.id] = member
                elif self.hashgraph.known_members[member.id].address is None:
                    self.hashgraph.known_members[member.id].address = member.address

    def start_push_thread(self) -> None:
        self.background_push_client_thread = PushingClientThread(self)
        self.background_push_client_thread.daemon = True
        self.background_push_client_thread.start()

    def stop_push_thread(self) -> None:
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
            self.network.push_to_random()
            time.sleep(max(random.normalvariate(bptc.push_waiting_time_mu, bptc.push_waiting_time_sigma), 0))

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
        self.q = queue.Queue(maxsize=1)

    def run(self):
        while not self.stopped():
            (data_string, peer) = self.q.get()
            self.network.process_data_string(data_string, peer)
            self.q.task_done()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class BootstrapPushThread(threading.Thread):
    def __init__(self, ip, port, network):
        threading.Thread.__init__(self)
        self.ip = ip
        self.port = port
        self.network = network

    def run(self):
        while len(self.network.hashgraph.known_members) == 1:
            self.network.push_to(self.ip, int(self.port))
            time.sleep(2)

def start_reactor_thread():
    thread = threading.Thread(target=partial(reactor.run, installSignalHandlers=0))
    thread.daemon = True
    thread.start()


def stop_reactor_thread():
    reactor.callFromThread(reactor.stop)


def register(member_id, listening_port, registry_ip, registry_port):
    factory = RegisterClientFactory(str(member_id), int(listening_port))

    def register():
        reactor.connectTCP(registry_ip, int(registry_port), factory)
    threads.blockingCallFromThread(reactor, register)


def process_query(client, members):
    for member_id, (ip, port) in members.items():
        if member_id != str(client.me.id):
            if member_id not in client.hashgraph.known_members:
                client.hashgraph.known_members[member_id] = Member(member_id, None)
            client.hashgraph.known_members[member_id].address = IPv4Address('TCP', ip, port)
            bptc.logger.debug('Member update: {}... to ({}, {})'.format(member_id[:6], ip, port))


def query_members(client, query_members_ip, query_members_port):
    factory = QueryMembersClientFactory(client, lambda x: process_query(client, x))

    def query():
        reactor.connectTCP(query_members_ip, int(query_members_port), factory)
    threads.blockingCallFromThread(reactor, query)


def start_listening(network, listening_ip, listening_port, allow_reset_signal):
    bptc.logger.info("Push server listens on port {}".format(listening_port))
    push_server_factory = PushServerFactory(network.receive_data_string_callback, allow_reset_signal, network)
    reactor.listenTCP(interface=listening_ip, port=int(listening_port), factory=push_server_factory)

    bptc.logger.info("[Pull server (for viz tool) listens on port {}]".format(int(listening_port) + 1))
    pull_server_factory = PullServerFactory(network.hashgraph.me.id, network.hashgraph)
    reactor.listenTCP(interface=listening_ip, port=int(listening_port) + 1, factory=pull_server_factory)

    # Push to yourself (is ignored when received)
    # This is a workaround for bug on some systems where the reactor ignores incoming connections until it
    # had at least one outgoing connection
    network.push_to_member(network.hashgraph.me, True)