import os
import threading

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout

from hptaler.data.member import Member
from hptaler.data.network import Network
from hptaler.data.hashgraph import Hashgraph

from networking.push_protocol import PushServerFactory
from networking.pull_protocol import PullServerFactory
from twisted.internet import reactor, threads
import random
from networking.query_members_protocol import QueryMembersClientFactory
from networking.register_protocol import RegisterClientFactory
from utilities.log_helper import logger
from kivy.config import Config
from hptaler.data.db import DB

Config.set('graphics', 'width', '600')
Config.set('graphics', 'height', '150')

# import gi
# gi.require_version('Gtk', '3.0')


# https://github.com/kivy/kivy/wiki/Working-with-Python-threads-inside-a-Kivy-application
class Core(GridLayout):

    def __init__(self, network, args):
        self.args = args
        Builder.load_file(os.path.join('res', 'wallet_layout.kv'))
        super().__init__()

        self.network = network
        self.hashgraph = network.hashgraph
        self.me = network.hashgraph.me

        # Set up UI
        self.stop = threading.Event()
        self.add_widget(Label(text='Member ID: {}'.format(self.me.id)))
        self.add_widget(Button(text='start listening on', on_press=self.start_listening))
        self.listening_port_input = TextInput(text='8000')
        self.add_widget(self.listening_port_input)
        self.add_widget(Button(text='heartbeat', on_press=self.heartbeat))
        self.add_widget(Button(text='push to', on_press=self.push))
        self.add_widget(Button(text='push to random', on_press=self.push_to_random))
        self.push_to_ip_input = TextInput(text='localhost')
        self.add_widget(self.push_to_ip_input)
        self.push_to_port_input = TextInput(text='8000')
        self.add_widget(self.push_to_port_input)
        self.add_widget(Button(text='register at', on_press=self.register))
        self.registry_ip_input = TextInput(text='localhost')
        self.add_widget(self.registry_ip_input)
        self.registry_register_port_input = TextInput(text='8010')
        self.add_widget(self.registry_register_port_input)
        self.add_widget(Button(text='query members from', on_press=self.query_members))
        self.registry_query_port_input = TextInput(text='8011')
        self.add_widget(self.registry_query_port_input)

    # def start_loop_thread(self, *args):
    #     def loop():
    #         iteration = 0
    #         while True:
    #             if self.stop.is_set():
    #                 # Stop running this thread so the main Python process can exit.
    #                 return
    #             iteration += 1
    #             logger.info('#{}'.format(iteration))
    #             self.step()
    #             time.sleep(2)
    #
    #     logger.info("Starting event loop...")
    #     threading.Thread(target=loop).start()

    def heartbeat(self, *args):
        self.network.heartbeat()

    def push(self, *args):
        self.network.push_to(self.push_to_ip_input.text, int(self.push_to_port_input.text))

    def push_to_random(self, *args):
        self.network.push_to_random()

    def register(self, *args):
        factory = RegisterClientFactory(str(self.me.id), int(self.listening_port_input.text))

        def register():
            reactor.connectTCP(self.registry_ip_input.text, int(self.registry_register_port_input.text), factory)
        threads.blockingCallFromThread(reactor, register)

    def process_query(self, members):
        new_members = {}
        for member_id, (ip, port) in members.items():
            if member_id != str(self.me.id):
                new_members[member_id] = (ip, port)
                self.neighbours[member_id] = (ip, port)
        logger.info("Acquainted with {}".format(new_members))

    def query_members(self, *args):
        factory = QueryMembersClientFactory(self, self.process_query)

        def query():
            reactor.connectTCP(self.registry_ip_input.text, int(self.registry_query_port_input.text), factory)
        threads.blockingCallFromThread(reactor, query)

    def start_listening(self, *args):
        port = int(self.listening_port_input.text)
        logger.info("Push server listens on port {}".format(port))
        push_server_factory = PushServerFactory(self.network.receive_events_callback)
        reactor.listenTCP(port, push_server_factory)

        logger.info("[Pull server (for viz tool) listens on port {}]".format(port + 1))

        pull_server_factory = PullServerFactory(self.network)
        reactor.listenTCP(port + 1, pull_server_factory)


class HPTWallet(App):

    def __init__(self, args):
        super().__init__()
        self.args = args

        # Try to load the Hashgraph from the database
        self.hashgraph = DB.load_hashgraph()
        create_initial_event = False

        # Create a new hashgraph if it could not be loaded
        if self.hashgraph is None or self.hashgraph.me is None:
            self.me = Member.create()
            self.hashgraph = Hashgraph(self.me)
            create_initial_event = True

        # Create network
        self.network = Network(self.hashgraph, create_initial_event)

        self.start_reactor_thread()

    @staticmethod
    def start_reactor_thread():
        def start_reactor():
            reactor.run(installSignalHandlers=0)

        threading.Thread(target=start_reactor).start()

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        logger.info("Stopping...")
        DB.save(self.network.hashgraph)
        reactor.callFromThread(reactor.stop)
        self.root.stop.set()

    def build(self):
        self.title = 'HPT Wallet'
        return Core(self.network, self.args)


def main():
    #parser = argparse.ArgumentParser(description='HPT Wallet')
    #parser.add_argument('--id', type=int, help='command line id for dev')
    #args = parser.parse_args()
    args = ()
    HPTWallet(args).run()

if __name__ == '__main__':
    main()
