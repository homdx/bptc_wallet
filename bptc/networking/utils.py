import threading
from functools import partial

from twisted.internet import reactor, threads
from twisted.internet.address import IPv4Address

from bptc.data.member import Member
import bptc.utils as utils
from .push_protocol import PushServerFactory
from .query_members_protocol import QueryMembersClientFactory
from .register_protocol import RegisterClientFactory
from .pull_protocol import PullServerFactory

def initial_checks(app):
    # starts network client in a new thread
    start_reactor_thread()
    # listen to hashgraph actions
    start_listening(app.network, app.cl_args.port)
    if app.cl_args.register:
        ip, port = app.cl_args.register.split(':')
        register(app.me.id, app.cl_args.port, ip, port)
        port = str(int(port) + 1)
        threading.Timer(2, query_members,
                        args=(app, ip, port)).start()


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
            utils.logger.info('Member update: {}... to ({}, {})'.format(member_id[:6], ip, port))


def query_members(client, query_members_ip, query_members_port):
    factory = QueryMembersClientFactory(client, lambda x: process_query(client, x))

    def query():
        reactor.connectTCP(query_members_ip, int(query_members_port), factory)
    threads.blockingCallFromThread(reactor, query)


def start_listening(network, listening_port):
    utils.logger.info("Push server listens on port {}".format(listening_port))
    push_server_factory = PushServerFactory(network.receive_events_callback,
                                            network.receive_members_callback)
    reactor.listenTCP(int(listening_port), push_server_factory)
    network.me.address = IPv4Address("TCP", "127.0.0.1", listening_port)

    utils.logger.info("[Pull server (for viz tool) listens on port {}]".format(int(listening_port) + 1))
    pull_server_factory = PullServerFactory(network)
    reactor.listenTCP(int(listening_port) + 1, pull_server_factory)
