#!/usr/bin/python3
import os
import sqlite3

import matplotlib
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

def plot_runtime():
    font = {'family': 'normal',
            'weight': 'bold',
            'size': 22}
    matplotlib.rc('font', **font)

    x = []
    y_total_time = []
    y_divide_rounds_time = []
    y_decide_fame_time = []
    y_find_order_time = []
    for i in range(100, 2600, 100):
        db_file = 'test_setup/1/data/data{}.db'.format(i)
        print('Processing file {}'.format(db_file))
        x_, total_time_, divide_rounds_time_, decide_fame_time_, find_order_time_ = analyze_runtime(db_file)
        x.append(x_)
        y_total_time.append(total_time_)
        y_divide_rounds_time.append(divide_rounds_time_)
        y_decide_fame_time.append(decide_fame_time_)
        y_find_order_time.append(find_order_time_)

    plt.plot(x, y_total_time, 'r')
    plt.plot(x, y_total_time, 'ro')
    red_patch = mpatches.Patch(color='red', label='total time')

    plt.plot(x, y_divide_rounds_time, 'b')
    plt.plot(x, y_divide_rounds_time, 'bo')
    blue_patch = mpatches.Patch(color='blue', label='divide rounds')

    plt.plot(x, y_decide_fame_time, 'y')
    plt.plot(x, y_decide_fame_time, 'yo')
    yellow_patch = mpatches.Patch(color='yellow', label='decide fame')

    plt.plot(x, y_find_order_time, 'g')
    plt.plot(x, y_find_order_time, 'go')
    green_patch = mpatches.Patch(color='green', label='find order')

    plt.legend(handles=[red_patch, blue_patch, yellow_patch, green_patch])
    plt.ylabel('processing time [s]')
    plt.xlabel('events')
    plt.show()


def plot_db_size():
    font = {'family': 'normal',
            'weight': 'bold',
            'size': 22}
    matplotlib.rc('font', **font)

    x = []
    y_size = []
    for i in range(100, 5100, 100):
        db_file = 'test_setup/1/data/data{}.db'.format(i)
        print('Processing file {}'.format(db_file))
        y_size_ = os.path.getsize(db_file)/float(1024)
        x.append(i)
        y_size.append(y_size_)

    plt.plot(x, y_size, 'r')
    plt.plot(x, y_size, 'ro')
    red_patch = mpatches.Patch(color='red', label='db size')

    plt.legend(handles=[red_patch])
    plt.ylabel('db size [kB]')
    plt.xlabel('events')
    plt.show()

if __name__ == '__main__':
    init_logger('tools/db_analyzer_log.txt')
    bptc.logger.removeHandler(bptc.stdout_logger)
    plot_db_size()

    # data1 = create_confirmation_length_data('./test_setup/4c_1pps/data/data.db')
    # data2 = create_confirmation_length_data('./test_setup/4c_2pps/data/data.db')
    # data3 = create_confirmation_length_data('./test_setup/8c_1pps/data/data.db')
    # data4 = create_confirmation_length_data('./test_setup/8c_2pps/data/data.db')

    # plot_boxplot([data1, data2, data3, data4], ['4 clients, 1000 push/s', '4 clients, 2 push/s',
    #                                            '8 clients, 1000 push/s', '8 clients, 2 push/s'],
    #             'confirmation length [s]')


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