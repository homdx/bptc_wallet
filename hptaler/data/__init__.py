from hptaler.data.member import Member
from hptaler.data.network import Network

from utilities.log_helper import logger


def main():
    # Create my account
    me: Member = Member.create()

    # Create the network
    network: Network = Network(me)

    # Add some heartbeats
    #for _ in range(5):
    #    network.heartbeat()




if __name__ == '__main__':
    main()
