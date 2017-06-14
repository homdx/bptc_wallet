import argparse
from bptc.client.mobile import MobileApp

__version__ = "0.1"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", type=int, default=8000,
                        help="Porting for pulling information from other members and the registry")
    return parser.parse_args()


if __name__ == '__main__':
    # Right now there is only one app designed for mobile devives
    MobileApp(parse_args()).run()
