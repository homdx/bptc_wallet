import os
import sqlite3

import dateutil.parser

from bptc.data.event import Event

db_dir = './../test_setup/4_gui_member/1/data'


class DB:

    __connection = None

    @classmethod
    def __connect(cls) -> None:
        """
        Connects to the database. Creates a new database if necessary
        :return: None
        """
        if cls.__connection is None:
            # Connect to DB
            database_file = os.path.join(db_dir, 'data.db')
            cls.__connection = sqlite3.connect(database_file)

        else:
            print("Database has already been connected")

    @classmethod
    def __get_cursor(cls) -> sqlite3:
        # Connect to DB on first call
        if cls.__connection is None:
            cls.__connect()
        return cls.__connection.cursor()

    @classmethod
    def load_events(cls):
        print('Loading {}/data.db...'.format(db_dir))

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
                print("Event had invalid signature: {}".format(event))
                raise AssertionError("Event had invalid signature: {}".format(event))

        print('Loaded {} events from DB.'.format(len(events)))
        return events


if __name__ == '__main__':
    events = DB.load_events()
    for event in events.values():
        if event.confirmation_time is not None:
            creation_time = dateutil.parser.parse(event.time)
            confirmation_time = dateutil.parser.parse(event.confirmation_time)
            difference = (confirmation_time - creation_time).total_seconds()
            if difference < 100:
                print(difference)
