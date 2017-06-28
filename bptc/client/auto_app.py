import sys
import time

from prompt_toolkit import prompt

import bptc
import bptc.networking.utils as network_utils
from bptc.data.db import DB
from main import __version__
from bptc.data.hashgraph import init_hashgraph


class AutoApp():
    def __init__(self, cl_args):
        self.cl_args = cl_args
        bptc.logger.info('BPTC Wallet {} Auto Client'.format(__version__))
        self.me = None
        self.hashgraph = None
        self.network = None
        init_hashgraph(self)

    def __call__(self):
        network_utils.initial_checks(self)
        try:
            bptc.logger.info('Automatically query members, push randomly, listen to events and create heartbeats')
            while True:
                self.query_members()
                self.network.start_background_pushes()
                self.run()
                time.sleep(5)
        except (EOFError, KeyboardInterrupt):
            print('Good bye!')
        except:
            print('{} thrown -> GoodBye!'.format(sys.exc_info()[0].__name__))
            raise
        finally:
            bptc.logger.info("Stopping...")
            DB.save(self.network.hashgraph)
            network_utils.stop_reactor_thread()

    def run(self):
        # TODO: Maybe add registering if not successfully until now
        self.network.heartbeat()

    def query_members(self):
        ip, port = self.cl_args.query_members.split(':')
        network_utils.query_members(self, ip, port)
