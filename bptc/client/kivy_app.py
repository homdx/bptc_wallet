import os
# Ignore command line arguments in Kivy
import threading

os.environ["KIVY_NO_ARGS"] = "1"
from kivy.app import App
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager
import bptc
import bptc.utils.network as network_utils
from bptc.client.kivy_screens import MainScreen, NewTransactionScreen, TransactionsScreen, PublishNameScreen, DebugScreen
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph

# size of an iPhone 6 Plus
Config.set('graphics', 'width', '414')
Config.set('graphics', 'height', '736')


class KivyApp(App):
    def __init__(self, cl_args):
        self.cl_args = cl_args
        self.title = 'BPTC Wallet'
        super().__init__()
        self.network = None
        init_hashgraph(self)
        # starts network client in a new thread
        network_utils.start_reactor_thread()
        # listen to hashgraph actions
        network_utils.start_listening(self.network, self.cl_args.port, self.cl_args.dirty)

    def build(self):
        defaults = {
            'listening_port': self.cl_args.port,
            'push_address': 'localhost:8000',
            'registering_address': 'localhost:9000',
            'query_members_address': 'localhost:9001',
            'member_id': self.network.me.formatted_name
        }

        sm = ScreenManager()
        sm.add_widget(MainScreen(self.network, defaults))
        sm.add_widget(NewTransactionScreen(self.network))
        sm.add_widget(TransactionsScreen(self.network))
        debug_screen = PublishNameScreen(self.network)
        sm.add_widget(debug_screen)
        sm.add_widget(DebugScreen(self.network, defaults))

        if self.cl_args.register:
            ip, port = self.cl_args.register.split(':')
            network_utils.register(self.me.id, self.cl_args.port, ip, port)
            port = str(int(port) + 1)
            threading.Timer(2, network_utils.query_members,
                            args=(self, ip, port)).start()

        if self.cl_args.start_pushing:
            self.network.start_background_pushes()
            debug_screen.pushing = True

        if self.cl_args.bootstrap_push:
            ip, port = self.cl_args.bootstrap_push.split(':')
            self.network.push_to(ip, int(port))

        return sm

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        bptc.logger.info("Stopping...")
        network_utils.stop_reactor_thread()
        DB.save(self.network.hashgraph)
