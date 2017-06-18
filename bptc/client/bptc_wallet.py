import threading
from kivy.app import App
from argparse import Namespace

from bptc.data.db import DB
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member
from bptc.data.network import Network
import bptc.utils as utils
import bptc.networking.utils as network_utils


class BPTCWallet(App):
    def __init__(self, cl_args):
        self.cl_args = cl_args
        self.title = 'BPTC Wallet'
        super().__init__()
        self.init_hashgraph()

    def init_hashgraph(self):
        # Try to load the Hashgraph from the database
        self.hashgraph = DB.load_hashgraph(
            self.cl_args.port, self.cl_args.output)
        # Create a new hashgraph if it could not be loaded
        if self.hashgraph is None or self.hashgraph.me is None:
            self.me = Member.create()
            self.hashgraph = Hashgraph(self.me)
            self.network = Network(self.hashgraph, create_initial_event=True)
        else:
            self.network = Network(self.hashgraph, create_initial_event=False)
        # Starts network client in a new thread
        network_utils.start_reactor_thread()

    def on_stop(self):
        # The Kivy event loop is about to stop, set a stop signal;
        # otherwise the app window will close, but the Python process will
        # keep running until all secondary threads exit.
        utils.logger.info("Stopping...")
        DB.save(self.network.hashgraph)
        network_utils.stop_reactor_thread()
        self.root.stop.set()
