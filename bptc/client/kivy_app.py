import os
# Ignore command line arguments in Kivy
os.environ["KIVY_NO_ARGS"] = "1"
from kivy.app import App
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager

import bptc
import bptc.utils.network as network_utils
from bptc.client.kivy_screens import MainScreen, NewTransactionScreen, TransactionsScreen, PublishNameScreen
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
        self.me = None
        self.hashgraph = None
        self.network = None
        init_hashgraph(self)
        network_utils.initial_checks(self)  # c: name is misleading

    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(self.network, self.cl_args))
        sm.add_widget(NewTransactionScreen(self.network))
        sm.add_widget(TransactionsScreen(self.network))
        sm.add_widget(PublishNameScreen(self.network))
        return sm

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        bptc.logger.info("Stopping...")
        network_utils.stop_reactor_thread()
        DB.save(self.network.hashgraph)
