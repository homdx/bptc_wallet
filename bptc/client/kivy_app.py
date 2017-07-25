import os
from bptc.data.network import BootstrapPushThread
from kivy.app import App
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager
import bptc
import bptc.data.network as network_utils
from bptc.client.kivy_screens import MainScreen, NewTransactionScreen, TransactionsScreen, PublishNameScreen, \
    DebugScreen, MembersScreen
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph

os.environ["KIVY_NO_ARGS"] = "1"  # Ignore command line arguments in Kivy

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
        # start network client in a new thread
        network_utils.start_reactor_thread()
        # start listening to network communication
        network_utils.start_listening(self.network, bptc.ip, bptc.port, self.cl_args.dirty)

    def build(self):
        defaults = {
            'listening_port': bptc.port,
            'push_address': bptc.ip + ':8000',
            'registering_address': bptc.ip + ':9000',
            'query_members_address': bptc.ip + ':9001',
            'member_id': self.network.me.formatted_name
        }

        sm = ScreenManager()
        sm.add_widget(MainScreen(self.network, defaults))
        sm.add_widget(NewTransactionScreen(self.network))
        sm.add_widget(TransactionsScreen(self.network))
        sm.add_widget(MembersScreen(self.network))
        PublishNameScreen(self.network)
        sm.add_widget(PublishNameScreen(self.network))
        debug_screen = DebugScreen(self.network, defaults, self)
        sm.add_widget(debug_screen)

        # start a thread that pushes frequently
        self.network.start_push_thread()
        debug_screen.pushing = True

        # push to a specific network address until knowing other members
        if self.cl_args.bootstrap_push:
            ip, port = self.cl_args.bootstrap_push.split(':')
            thread = BootstrapPushThread(ip, port, self.network)
            thread.daemon = True
            thread.start()

        return sm

    def on_stop(self):
        bptc.logger.info("Stopping...")
        self.network.stop_push_thread()
        network_utils.stop_reactor_thread()
        DB.save(self.network.hashgraph)
