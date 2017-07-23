#!/usr/bin/python3

import argparse
import os
import bptc
from bptc import init_logger

__version__ = '0.1'


def parse_args():
    """Return the parsed command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument('-ip', type=str, default='0.0.0.0',
                        help='IP of network interface to use for listening. Use localhost if you don\'t want to '
                             'release your application for external devices.')
    parser.add_argument('-p', '--port', type=int, default=8000,
                        help='Port of network interface to use for listening.')
    parser.add_argument('-o', '--output', type=str, default='data',
                        help='Output directory for the sqlite3 database and log files')
    parser.add_argument('-cli', '--console', action='store_true', help='Use the interactive shell')
    parser.add_argument('--headless', action='store_true', help='Headless client')
    parser.add_argument('-v', '--verbose', action='store_true', help='Log to stdout in debug mode')
    parser.add_argument('--dirty', action='store_true',
                        help='This allows other clients to send a signal resetting ' +
                        'your local hashgraph. This is only available for the HeadlessApp.')
    parser.add_argument('-bp', '--bootstrap-push', type=str, default=None,
                        help='Push initially to the given address')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Store hashgraph in a temporary database for each 200 processed events')
    args = parser.parse_args()
    if not args.headless and args.dirty:
        args.dirty = False  # Ignore this flag on every other client
        print('WARN: The dirty command will be ignored! See the manual for further information.')
    return args

if __name__ == '__main__':
    cl_args = parse_args()
    bptc.ip = cl_args.ip
    bptc.port = cl_args.port
    os.makedirs(cl_args.output, exist_ok=True)
    init_logger(os.path.join(cl_args.output, 'log.txt'), cl_args.verbose)
    if cl_args.console:
        # start the console app
        from bptc.client.console_app import ConsoleApp
        ConsoleApp(cl_args)()
    elif cl_args.headless:
        # start the headless app
        from bptc.client.headless_app import HeadlessApp
        HeadlessApp(cl_args)()
    else:
        # start the kivy app
        from bptc.client.kivy_app import KivyApp
        KivyApp(cl_args).run()
