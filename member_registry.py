#!/usr/bin/python3

import threading
from twisted.internet import reactor
from bptc.networking.query_members_protocol import QueryMembersServerFactory
from bptc.networking.register_protocol import RegisterServerFactory
from prompt_toolkit import prompt


class MemberRegistry:
    def __init__(self):
        self.members = {}

    def __call__(self):
        try:
            self.start_reactor_thread()
            self.start_listening()
            print('Listening for registrations...')
            while True:
                prompt()
        except (EOFError, KeyboardInterrupt):
            print('Good bye!')
        except:
            print('{} thrown -> GoodBye!'.format(sys.exc_info()[0].__name__))
            raise
        finally:
            reactor.callFromThread(reactor.stop)

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        thread = threading.Thread(target=start_reactor)
        thread.daemon = True
        thread.start()

    def received_data_callback(self, member_id, port, info):
        print('Member {}... registered with ({}, {})'.format(member_id[:6], info.host, port))
        self.members[member_id] = (info.host, port)

    def start_listening(self, *args):
        factory1 = RegisterServerFactory(self.received_data_callback)
        reactor.listenTCP(9000, factory1)
        factory2 = QueryMembersServerFactory(self.members)
        reactor.listenTCP(9001, factory2)


def main():
    MemberRegistry()()

if __name__ == '__main__':
    main()
