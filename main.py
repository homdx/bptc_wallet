#!/usr/bin/python3

import argparse
import os
from bptc import init_logger

__version__ = '0.1'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000,
                        help='Porting for pulling information from other members and the registry')
    parser.add_argument('-o', '--output', type=str, default='data',
                        help='Output directory for the sqlite3 database and log files')
    parser.add_argument('-cli', '--console', action='store_true', help='Use the interactive shell')
    parser.add_argument('-auto', '--auto', action='store_true', help='Self organizing client')
    parser.add_argument('-r', '--register', type=str, default=None, help='Automatically register at given address')
    parser.add_argument('-qm', '--query-members', type=str, default='localhost:9001',
                        help='Address for querying members automatically')
    parser.add_argument('-sp', '--start-pushing', action='store_true', help='Start frequent pushing')
    parser.add_argument('-q', '--quiet', action='store_true', help='Less output as possible')
    parser.add_argument('--dirty', action='store_true',
                        help='This allows other clients to send a signal resetting ' +
                        'your local hashgraph. This is only available for the HeadlessApp.')
    parser.add_argument('-bp', '--bootstrap-push', type=str, default='localhost:8000',
                        help='Push initially to the given address')
    args = parser.parse_args()
    if not args.auto and args.dirty:
        args.dirty = False  # Ignore this flag on every other client
        print('WARN: The dirty command will be ignored! See the manual for further information.')
    return args

if __name__ == '__main__':
    # Right now there is only one app designed for mobile devices
    cl_args = parse_args()
    os.makedirs(cl_args.output, exist_ok=True)
    init_logger(os.path.join(cl_args.output, 'log.txt'), cl_args.quiet)
    if cl_args.console:
        from bptc.client.console_app import ConsoleApp
        ConsoleApp(cl_args)()
    elif cl_args.auto:
        from bptc.client.headless_app import HeadlessApp
        HeadlessApp(cl_args)()
    else:
        from bptc.client.kivy_app import KivyApp
        KivyApp(cl_args).run()
