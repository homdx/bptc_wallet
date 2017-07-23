import sys
import time

import bptc
import bptc.utils.network as network_utils
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph
from main import __version__


class HeadlessApp():
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
            bptc.logger.info('Automatically query members, push randomly, listen to pushs')
            self.network.start_push_thread()
            while True:
                self.query_members()
                time.sleep(30)
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
        pass

    def query_members(self):
        ip, port = self.cl_args.query_members.split(':')
        network_utils.query_members(self, ip, port)
