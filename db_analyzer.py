#!/usr/bin/python3

import sqlite3
import matplotlib.pyplot as plt
import dateutil.parser
import bptc
from bptc import init_logger
from bptc.data.event import Event
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member
import time
import matplotlib.patches as mpatches

db_file = None


class DBLoader:

    __connection = None

    @classmethod
    def connect(cls, db_file):
        if cls.__connection:
            cls.__connection.close()

        cls.__connection = sqlite3.connect(db_file)

    @classmethod
    def __get_cursor(cls) -> sqlite3:
        # Connect to DB on first call
        if cls.__connection is None:
            print('Connect first!')
            return
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


def plot_boxplot(data, x_labels, y_label):
    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.boxplot(data)
    ax.set_xticklabels(x_labels)
    ax.set_ylabel(y_label)
    plt.show()


def create_confirmation_length_data(db_dile):
    DBLoader.connect(db_dile)
    other_events = DBLoader.load_events()
    data = get_confirmation_length(other_events)
    return list(filter(lambda x: x < 100, data))


def analyze_runtime(db_file):
    DBLoader.connect(db_file)
    other_events = DBLoader.load_events()
    other_members, other = DBLoader.load_members()
    me = Member.create()
    my_hashgraph = Hashgraph(me)
    start_time = time.time()
    divide_rounds_time, decide_fame_time, find_order_time = my_hashgraph.process_events(other, other_events)
    total_time = time.time() - start_time
    return len(other_events), total_time, divide_rounds_time, decide_fame_time, find_order_time

if __name__ == '__main__':
    init_logger('tools/db_analyzer_log.txt')
    bptc.logger.removeHandler(bptc.stdout_logger)

    # data1 = create_confirmation_length_data('./test_setup/4c_1pps/data/data.db')
    # data2 = create_confirmation_length_data('./test_setup/4c_2pps/data/data.db')
    # data3 = create_confirmation_length_data('./test_setup/8c_1pps/data/data.db')
    # data4 = create_confirmation_length_data('./test_setup/8c_2pps/data/data.db')

    # plot_boxplot([data1, data2, data3, data4], ['4 clients, 1000 push/s', '4 clients, 2 push/s',
    #                                            '8 clients, 1000 push/s', '8 clients, 2 push/s'],
    #             'confirmation length [s]')

    x1, total_time1, divide_rounds_time1, decide_fame_time1, find_order_time1 = analyze_runtime('test_setup/200/data/data.db')
    x2, total_time2, divide_rounds_time2, decide_fame_time2, find_order_time2 = analyze_runtime('test_setup/400/data/data.db')
    x3, total_time3, divide_rounds_time3, decide_fame_time3, find_order_time3 = analyze_runtime('test_setup/600/data/data.db')
    x4, total_time4, divide_rounds_time4, decide_fame_time4, find_order_time4 = analyze_runtime('test_setup/800/data/data.db')
    x5, total_time5, divide_rounds_time5, decide_fame_time5, find_order_time5 = analyze_runtime('test_setup/1000/data/data.db')

    x = [x1, x2, x3, x4, x5]

    y = [total_time1, total_time2, total_time3, total_time4, total_time5]
    plt.plot(x, y, 'r')
    plt.plot(x, y, 'ro')
    red_patch = mpatches.Patch(color='red', label='total time')

    y = [divide_rounds_time1, divide_rounds_time2, divide_rounds_time3, divide_rounds_time4, divide_rounds_time5]
    plt.plot(x, y, 'b')
    plt.plot(x, y, 'bo')
    blue_patch = mpatches.Patch(color='blue', label='divide rounds')

    y = [decide_fame_time1, decide_fame_time2, decide_fame_time3, decide_fame_time4, decide_fame_time5]
    plt.plot(x, y, 'y')
    plt.plot(x, y, 'yo')
    yellow_patch = mpatches.Patch(color='yellow', label='decide fame')

    y = [find_order_time1, find_order_time2, find_order_time3, find_order_time4, find_order_time5]
    plt.plot(x, y, 'g')
    plt.plot(x, y, 'go')
    green_patch = mpatches.Patch(color='green', label='find order')

    plt.legend(handles=[red_patch, blue_patch, yellow_patch, green_patch])
    plt.ylabel('processing time [s]')
    plt.xlabel('events')
    plt.show()

    # memory
    # size_of_db = os.path.getsize(db_file)/float(1024)
    # bptc.logger.info('Size of DB: {} kB'.format(size_of_db))
    # avg_event_size = size_of_db/len(other_events1)
    # bptc.logger.info('Avg. size of event: {} kB'.format(avg_event_size))


'''
Timing code for hashgraph:

        import time
        start_time = time.time()
        divide_rounds(self, toposort(new_events))
        divide_rounds_time = time.time() - start_time
        start_time = time.time()
        decide_fame(self)
        decide_fame_time = time.time() - start_time
        start_time = time.time()
        find_order(self)
        find_order_time = time.time() - start_time
        self.process_ordered_events()
        return divide_rounds_time, decide_fame_time, find_order_time
'''