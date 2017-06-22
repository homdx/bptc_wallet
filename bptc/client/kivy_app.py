from kivy.app import App
from bptc.client.kivy_core import MainScreen, NewTransactionScreen
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph
import bptc.utils as utils
import bptc.networking.utils as network_utils
from kivy.config import Config
from kivy.uix.screenmanager import ScreenManager

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
        network_utils.initial_checks(self)

    def build(self):
        sm = ScreenManager()
        sm.add_widget(MainScreen(self.network, self.cl_args))
        sm.add_widget(NewTransactionScreen(self.network))
        return sm

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        utils.logger.info("Stopping...")
        DB.save(self.network.hashgraph)
        network_utils.stop_reactor_thread()
        #self.root.stop.set()
