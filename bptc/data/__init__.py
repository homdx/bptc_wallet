from bptc.data.member import Member
from bptc.data.network import Network

from utilities.log_helper import logger


def main():
    # Create my account
    me = Member.create()

    # Create the network
    network = Network(me)

    # Add some heartbeats
    #for _ in range(5):
    #    network.heartbeat()




if __name__ == '__main__':
    main()
