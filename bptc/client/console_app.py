import signal
import itertools
from functools import partial
from prompt_toolkit.shortcuts import confirm, prompt
import bptc
import bptc.utils.network as network_utils
from bptc.data.db import DB
from bptc.data.hashgraph import init_hashgraph
from bptc.data.network import BootstrapPushThread
from bptc.utils.interactive_shell import InteractiveShell
from main import __version__
from bptc.data.transaction import TransactionStatus, MoneyTransaction


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
            toggle_pushing=dict(
                help='Start/Stop pushing to randomly chosen clients',
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
            status=dict(
                help='Print information about the current hashgraph state',
            ),
            members=dict(
                help='Show all members withing the hashgraph network',
            ),
            send=dict(
                help='Send money to another member of the hashgraph network',
                args=[
                    (['amount'], dict(help='Amount of money', type=int)),
                    (['receiver'], dict(help='ID or name of the user which should receive the money')),
                    (['-c', '--comment'], dict(help='Comment related to your transaction', default='')),
                ],
            ),
            history=dict(help='List all relevant transactions'),
            verbose=dict(help='Toggle info level of stdout logger'),
        )
        super().__init__('BPTC Wallet {} CLI'.format(__version__))
        self.network = None
        self.pushing = False
        init_hashgraph(self)

    @property
    def hashgraph(self):
        return self.network.hashgraph

    @property
    def me(self):
        return self.network.hashgraph.me

    def __call__(self):
        if hasattr(signal, 'SIGHUP'):
            signal.signal(signal.SIGHUP, partial(self.exit, self))
        elif hasattr(signal, 'SIGTERM'):
            # On windows listen to SIGTERM because SIGHUP is not available
            signal.signal(signal.SIGTERM, partial(self.exit, self))

        try:
            print(
                'WARN: Receiving and pushing events might cover over the console ' +
                'interface. Press Ctrl + V or call command verbose to turn this ' +
                'behaviour on or off. \n' +
                'Press any key to continue...')
            prompt('')
            # starts network client in a new thread
            network_utils.start_reactor_thread()
            # listen to hashgraph actions
            network_utils.start_listening(self.network, self.cl_args.ip, self.cl_args.port, self.cl_args.dirty)

            if self.cl_args.start_pushing:
                self.network.start_background_pushes()

            if self.cl_args.bootstrap_push:
                ip, port = self.cl_args.bootstrap_push.split(':')
                thread = BootstrapPushThread(ip, port, self.network)
                thread.daemon = True
                thread.start()

            super().__call__()
        # Ctrl+C throws KeyBoardInterruptException, Ctrl+D throws EOFException
        finally:
            self.exit()
        # TODO: If no command was entered and Ctrl+C was hit, the process doesn't stop

    def exit(self, signum=None, frame=None):
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

    def cmd_toggle_pushing(self, args):
        if not self.pushing:
            bptc.logger.info('Start pushing randomly')
            self.network.start_background_pushes()
            self.pushing = True
        else:
            bptc.logger.info('Stop pushing randomly')
            self.network.stop_background_pushes()
            self.pushing = False

    def cmd_reset(self, args):
        do_it = confirm('Are you sure you want to reset the local hashgraph? (y/n) ')
        if do_it:
            bptc.logger.warn('Deleting local database containing the hashgraph')
            self.network.reset(self)

    def cmd_status(self, args):
        bptc.logger.info('I am: {}'.format(repr(self.me)))
        bptc.logger.info('Account balance: {} BPTC'.format(self.me.account_balance))
        bptc.logger.info('{} events, {} confirmed'.format(len(self.hashgraph.lookup_table.keys()),
                                                          len(self.hashgraph.ordered_events)))
        bptc.logger.info('Last push sent: {}'.format(self.network.last_push_sent))
        bptc.logger.info('Last push received: {}'.format(self.network.last_push_received))

    def cmd_send(self, args):
        # Generate mapping from a string to members
        members = list(self.network.hashgraph.known_members.values())
        members = [m for m in members if m != self.network.me]
        member_names = dict(itertools.chain(
            ((m.name, m) for m in members if m.name is not None and len(self.name) != 0),
            ((m.id[:6], m) for m in members),
            ((m.id, m) for m in members),
        ))
        # Check if the inserted string is within the member name mapping
        if args.receiver in member_names:
            receiver = member_names[args.receiver]
            bptc.logger.info("Transfering {} BPTC to {} with comment '{}'".format(args.amount, receiver, args.comment))
            self.network.send_transaction(args.amount, args.comment, receiver)
        else:
            bptc.logger.error('Invalid member name, call list_member to see all available options.')

    def cmd_members(self, args):
        members = self.network.hashgraph.known_members.values()
        members = [m for m in members if m != self.network.me]
        members.sort(key=lambda x: x.formatted_name)
        members_list = '\n'.join('{}. {}'.format(i+1, repr(m)) for i, m in enumerate(members))
        bptc.logger.info('Members List:\n{}'.format(members_list))

    def cmd_history(self, args):
        transactions = self.network.hashgraph.get_relevant_transactions(plain=True)
        transactions_list = '\n'.join('{}. {}'.format(
            i+1, t['formatted']) for i, t in enumerate(transactions))
        bptc.logger.info('Transactions List:\n{}'.format(transactions_list))

    def cmd_verbose(self, args):
        bptc.toggle_stdout_logger()
        print(bptc.stdout_logger.level)
