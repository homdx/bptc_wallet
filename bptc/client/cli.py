import sys
import argparse

from main import __version__
from bptc.utils import InteractiveShell
from bptc.data.db import DB
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member
from bptc.data.network import Network
import bptc.utils as utils
import bptc.networking.utils as network_utils


class ConsoleApp(InteractiveShell):
    def __init__(self, cl_args):
        self.cl_args = cl_args
        self.commands = dict(
            push=dict(
                help = 'Send local hashgraph to another client',
                args=[
                    (['target'], dict(default='localhost:8000', nargs='?',
                     help='Target address (incl. port)'))
                ],
            ),
            push_random=dict(
                help = 'Send local hashgraph to another random chosen client',
            ),
            register=dict(
                help = 'Register this hashgraph member at the registry',
                args=[
                    (['target'], dict(default='localhost:9000',
                     nargs='?', help='Registry address (incl. port)'))
                ],
            ),
            query_members=dict(
                help = 'Query network members from registry',
                args=[
                    (['target'], dict(default='localhost:9001',
                     nargs='?', help='Registry address (incl. port)'))
                ],
            ),
            heartbeat=dict(
                help = 'Create heartbeat event and add it to the hashgraph',
            ),
        )
        super().__init__('BPTC Wallet CLI {}'.format(__version__))
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
            self.me = self.hashgraph.me
        print('Member name: {}'.format(self.me.formatted_name))
        # Starts network client in a new thread
        network_utils.start_reactor_thread()
        # Listen to hashgraph actions
        self.start_listening()

    def __call__(self):
        try:
            super().__call__()
        finally:
            network_utils.stop_reactor_thread()

    # --------------------------------------------------------------------------
    # Hashgraph actions
    # --------------------------------------------------------------------------

    def start_listening(self):
        network_utils.start_listening(self.network, self.cl_args.port)

    def cmd_register(self, args):
        ip, port = args.target.split(':')
        network_utils.register(self.me.id, self.cl_args.port, ip, port)

    def cmd_query_members(self, args):
        ip, port = args.target.split(':')
        network_utils.query_members(self, ip, port)

    def cmd_heartbeat(self, args):
        self.network.heartbeat()

    def cmd_push(self, args):
        ip, port = args.target.split(':')
        self.network.push_to(ip, int(port))

    def cmd_push_random(self, args):
        self.network.push_to_random()
