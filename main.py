import os
import argparse
from bptc.utils import init_logger
from bptc.client.mobile import MobileApp

__version__ = '0.1'


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000,
                        help='Porting for pulling information from other members and the registry')
    parser.add_argument('-o', '--output', type=str, default='data',
                        help='Output directory for the sqlite3 database and log files')
    return parser.parse_args()

if __name__ == '__main__':
    # Right now there is only one app designed for mobile devices
    cl_args = parse_args()
    os.makedirs(cl_args.output, exist_ok=True)
    init_logger(cl_args.output)
    MobileApp(cl_args).run()
