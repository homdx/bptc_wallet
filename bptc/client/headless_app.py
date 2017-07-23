import sys
import time
import bptc
import bptc.utils.network as network_utils
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph
from main import __version__


class HeadlessApp:
    def __init__(self, cl_args):
        self.cl_args = cl_args
        bptc.logger.info('BPTC Wallet {} Auto Client'.format(__version__))
        self.me = None
        self.hashgraph = None
        self.network = None
        init_hashgraph(self)

    def __call__(self):
        # start network client in a new thread
        network_utils.start_reactor_thread()
        # start listening to network communication
        network_utils.start_listening(self.network, bptc.ip, bptc.port, self.cl_args.dirty)
        try:
            bptc.logger.info('Push randomly and listen to pushs')
            self.network.start_push_thread()
            while True:
                time.sleep(30)
        except (EOFError, KeyboardInterrupt):
            print('Good bye!')
        except:
            print('{} thrown -> GoodBye!'.format(sys.exc_info()[0].__name__))
            raise
        finally:
            bptc.logger.info("Stopping...")
            self.network.stop_push_thread()
            network_utils.stop_reactor_thread()
            DB.save(self.network.hashgraph)

    def run(self):
        # TODO: Maybe add registering if not successfully until now
        pass
