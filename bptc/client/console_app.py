import signal
from functools import partial
from prompt_toolkit.shortcuts import confirm

import bptc
import bptc.utils.network as network_utils
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph
from bptc.utils.interactive_shell import InteractiveShell
from main import __version__


class ConsoleApp(InteractiveShell):
    def __init__(self, cl_args):
        self.cl_args = cl_args
        self.commands = dict(
            push=dict(
                help='Send local hashgraph to another client',
                args=[
                    (['target'], dict(default='localhost:8000', nargs='?',
                     help='Target address (incl. port)'))
                ],
            ),
            push_random=dict(
                help='Start pushing to randomly chosen clients',
            ),
            register=dict(
                help='Register this hashgraph member at the registry',
                args=[
                    (['target'], dict(default=self.cl_args.register,
                     nargs='?', help='Registry address (incl. port)'))
                ],
            ),
            query_members=dict(
                help='Query network members from registry',
                args=[
                    (['target'], dict(default=self.cl_args.query_members,
                     nargs='?', help='Registry address (incl. port)'))
                ],
            ),
            reset=dict(
                help='Call this command to reset the local hashgraph',
                args=[
                    (['-f', '--force'], dict(action='store_true', help='Don\'t ask for permission'))
                ],
            ),
        )
        super().__init__('BPTC Wallet {} CLI'.format(__version__))
        self.network = None
        init_hashgraph(self)

    @property
    def hashgraph(self):
        return self.network.hashgraph

    @property
    def me(self):
        return self.network.me

    def __call__(self):
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, partial(self.SIGHUP_handler, self))
        elif hasattr(signal, 'SIGTERM'):
            # On windows listen to SIGTERM because SIGHUP is not available
            signal.signal(signal.SIGTERM, partial(self.SIGHUP_handler, self))
        try:
            network_utils.initial_checks(self)
            if self.cl_args.start_pushing:
                self.network.start_background_pushes()
            super().__call__()
        # Ctrl+C throws KeyBoardInterruptException, Ctrl+D throws EOFException
        finally:
            bptc.logger.info("Stopping...")
            network_utils.stop_reactor_thread()
            DB.save(self.network.hashgraph)
        # TODO: If no command was entered and Ctrl+C was hit, the process doesn't stop

    def SIGHUP_handler(self, signum, frame):
        bptc.logger.info("Stopping...")
        network_utils.stop_reactor_thread()
        DB.save(self.network.hashgraph)

    # --------------------------------------------------------------------------
    # Hashgraph actions
    # --------------------------------------------------------------------------

    def check_input(self, target):
        try:
            ip, port = target.split(':')
            return ip, port
        except ValueError:
            bptc.logger.error('Error: Unable to extract IP and port. Input was \'{}\''.format(target))
            return None, None

    def cmd_register(self, args):
        if args.target:
            ip, port = self.check_input(args.target)
            if not ip or not port:
                return
        else:
            ip, port = 'localhost', 9000
        network_utils.register(self.me.id, self.cl_args.port, ip, port)

    def cmd_query_members(self, args):
        if args.target:
            ip, port = self.check_input(args.target)
            if not ip or not port:
                return
        else:
            ip, port = 'localhost', 9001
        network_utils.query_members(self, ip, port)

    def cmd_push(self, args):
        ip, port = self.check_input(args.target)
        if not ip or not port:
            return
        self.network.push_to(ip, int(port))

    def cmd_push_random(self, args):
        self.network.start_background_pushes()

    def cmd_reset(self, args):
        do_it = confirm('Are you sure you want to reset the local hashgraph? (y/n) ')
        if do_it:
            bptc.logger.warn('Deleting local database containing the hashgraph')
            self.network.reset()
