import os
import sqlite3
import matplotlib.pyplot as plt
import dateutil.parser
import bptc
from bptc import init_logger
from bptc.data.event import Event
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member

db_file = './test_setup/1/data/data.db'


class DBLoader:

    __connection = None

    @classmethod
    def __connect(cls) -> None:
        """
        Connects to the database. Creates a new database if necessary
        :return: None
        """
        if cls.__connection is None:
            # Connect to DB
            cls.__connection = sqlite3.connect(db_file)

        else:
            bptc.logger.error("Database has already been connected")

    @classmethod
    def __get_cursor(cls) -> sqlite3:
        # Connect to DB on first call
        if cls.__connection is None:
            cls.__connect()
        return cls.__connection.cursor()

    @classmethod
    def load_events(cls):
        c = cls.__get_cursor()

        # Load events
        events = dict()
        for row in c.execute('SELECT * FROM events'):
            events[row[0]] = Event.from_db_tuple(row)

        # check parent links and signatures
        for event_id, event in events.items():
            if event.parents.self_parent is not None:
                if event.parents.self_parent not in events:
                    raise AssertionError("Events self_parent not in DB: {}".format(event))
            if event.parents.other_parent is not None:
                if event.parents.other_parent not in events:
                    raise AssertionError("Events other_parent not in DB: {}".format(event))
            if not event.has_valid_signature:
                raise AssertionError("Event had invalid signature: {}".format(event))

        bptc.logger.info('Loaded {} events from {}'.format(len(events), db_file))
        return events

    @classmethod
    def load_members(cls):
        c = cls.__get_cursor()

        # Load members
        me = None
        members = dict()
        for row in c.execute('SELECT * FROM members'):
            member = Member.from_db_tuple(row)
            members[member.id] = member
            if member.signing_key is not None:
                me = member

        bptc.logger.info('Loaded {} members from {}'.format(len(members), db_file))
        return members, me


def get_confirmation_length(events):
    d = []
    for event in events.values():
        if event.confirmation_time is not None:
            creation_time = dateutil.parser.parse(event.time)
            confirmation_time = dateutil.parser.parse(event.confirmation_time)
            confirmation_length = (confirmation_time - creation_time).total_seconds()
            d.append(confirmation_length)
    return d


def plot_boxplot(data):
    fig = plt.figure()
    fig.suptitle('Confimation length', fontsize=14, fontweight='bold')
    ax = fig.add_subplot(111)
    ax.boxplot(data)
    #ax.set_title('axes title')
    ax.set_xlabel('4 clients, 1 push/s')
    ax.set_xticklabels([])
    ax.set_ylabel('confirmation length [s]')

    plt.show()


if __name__ == '__main__':
    init_logger('tools/db_analyzer_log.txt')
    other_events = DBLoader.load_events()
    other_members, other = DBLoader.load_members()

    me = Member.create()
    my_hashgraph = Hashgraph(me)
    my_hashgraph.process_events(other, other_events)

    # memory
    size_of_db = os.path.getsize(db_file)/float(1024)
    bptc.logger.info('Size of DB: {} kB'.format(size_of_db))
    avg_event_size = size_of_db/len(other_events)
    bptc.logger.info('Avg. size of event: {} kB'.format(avg_event_size))

    # plot boxplot
    data = get_confirmation_length(other_events)
    data = list(filter(lambda x: x < 100, data))
    plot_boxplot(data)
