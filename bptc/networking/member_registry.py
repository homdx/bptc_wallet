import threading

from twisted.internet import reactor

from bptc.networking.query_members_protocol import QueryMembersServerFactory
from bptc.networking.register_protocol import RegisterServerFactory


class MemberRegistry:
    def __init__(self):
        self.members = {}
        self.start_reactor_thread()
        self.start_listening()

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        threading.Thread(target=start_reactor).start()

    def received_data_callback(self, member_id, port, info):
        self.members[member_id] = (info.host, port)

    def start_listening(self, *args):
        factory1 = RegisterServerFactory(self.received_data_callback)
        reactor.listenTCP(8010, factory1)
        factory2 = QueryMembersServerFactory(self.members)
        reactor.listenTCP(8011, factory2)


def main():
    registry = MemberRegistry()

if __name__ == '__main__':
    main()
