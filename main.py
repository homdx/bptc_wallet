import os
import argparse
from bptc.utils import init_logger

__version__ = '0.1'

def parse_args():
    parser = argparse.ArgumentParser(prog='main.py', add_help=False)
    group = parser.add_argument_group('Hashgraph Options')
    group.add_argument('-ah', '--help-app', action='store_true',
        help='Show this help message and exit')
    group.add_argument('-po', '--port', type=int, default=8000,
        help='Porting for pulling information from other members and the registry')
    group.add_argument('-o', '--output', type=str, default='data',
        help='Output directory for the sqlite3 database and log files')
    args, _ = parser.parse_known_args()
    if args.help_app:
        parser.print_help()
        parser.exit()
    return args

if __name__ == '__main__':
    # Right now there is only one app designed for mobile devives
    cl_args = parse_args()
    from bptc.client.mobile import MobileApp
    os.makedirs(cl_args.output, exist_ok=True)
    init_logger(cl_args.output)
    MobileApp(cl_args).run()
