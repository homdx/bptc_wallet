import os
import sqlite3
import bptc
from bptc.data.event import Event, Fame
from bptc.data.hashgraph import Hashgraph
from bptc.data.member import Member


class DB:

    __connection = None
    __listening_port = None
    __output_dir = None

    @classmethod
    def __connect(cls) -> None:
        """
        Connects to the database. Creates a new database if necessary
        :return: None
        """
        if cls.__connection is None:
            # Connect to DB
            database_file = os.path.join(cls.__output_dir, 'data.db')
            cls.__connection = sqlite3.connect(database_file)

            # Create tables if necessary
            c = cls.__connection.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS members (verify_key TEXT PRIMARY KEY, signing_key TEXT, head TEXT, stake INT, host TEXT, port INT, name TEXT)')
            c.execute('CREATE TABLE IF NOT EXISTS events (hash TEXT PRIMARY KEY, data TEXT, self_parent TEXT, other_parent TEXT, created_time DATETIME, verify_key TEXT, height INT, signature TEXT, round INT, witness BOOL, is_famous BOOL, round_received INT, consensus_time DATETIME)')

        else:
            bptc.logger.error("Database has already been connected")

    @classmethod
    def __get_cursor(cls) -> sqlite3:
        # Connect to DB on first call
        if cls.__connection is None:
            cls.__connect()
        return cls.__connection.cursor()

    @classmethod
    def __save_member(cls, m: Member) -> None:
        """
        Saves a Member object to the database
        :param m: The Member object to be saved
        :return: None
        """
        statement = 'INSERT OR REPLACE INTO members VALUES(?, ?, ?, ?, ?, ?, ?)'
        values = m.to_db_tuple()

        cls.__get_cursor().execute(statement, values)
        cls.__connection.commit()

    @classmethod
    def __save_event(cls, e: Event) -> None:
        """
        Saves an Event object to the database
        :param e: The Event object to be saved
        :return: None
        """
        statement = 'INSERT OR REPLACE INTO events VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'
        values = e.to_db_tuple()

        cls.__get_cursor().execute(statement, values)
        cls.__connection.commit()

    @classmethod
    def save(cls, obj) -> None:
        """
        Saves an object to the database
        :param obj: A Member object
        :return: None
        """
        if isinstance(obj, Member):
            cls.__save_member(obj)
        elif isinstance(obj, Event):
            cls.__save_event(obj)
        elif isinstance(obj, Hashgraph):
            cls.__save_member(obj.me)
            for _, member in obj.known_members.items():
                cls.__save_member(member)

            for _, event in obj.lookup_table.items():
                cls.__save_event(event)
        else:
            bptc.logger.error("Could not persist object because its type is not supported")

    @classmethod
    def load_hashgraph(cls, listening_port, output_dir) -> Hashgraph:
        cls.__listening_port = listening_port
        cls.__output_dir = output_dir
        c = cls.__get_cursor()

        # Load members
        me = None
        members = dict()
        for row in c.execute('SELECT * FROM members'):
            member = Member.from_db_tuple(row)
            members[member.id] = member
            if member.signing_key is not None:
                me = member

        # Load events
        events = dict()
        for row in c.execute('SELECT * FROM events'):
            events[row[0]] = Event.from_db_tuple(row)

        # Create hashgraph
        hg = Hashgraph(me)
        hg.known_members = members

        # check parent links and signatures
        for event_id, event in events.items():
            if event.parents.self_parent is not None:
                if event.parents.self_parent not in events:
                    raise AssertionError
            if event.parents.other_parent is not None:
                if event.parents.other_parent not in events:
                    raise AssertionError
            if not event.has_valid_signature:
                bptc.logger.warn("Event had invalid signature: {}".format(event))
                raise AssertionError

        hg.lookup_table = events

        # Create witness lookup
        for event_id, event in hg.lookup_table.items():
            if event.is_witness:
                hg.witnesses[event.round][event.verify_key] = event.id

        # Create fame lookup
        if len(hg.witnesses) > 0:
            for x_round in range(0, max(hg.witnesses) + 1):
                decided_witnesses_in_round_x_count = 0
                for x_id in hg.witnesses[x_round].values():
                    if hg.lookup_table[x_id] != Fame.UNDECIDED:
                        decided_witnesses_in_round_x_count += 1

                if decided_witnesses_in_round_x_count == len(hg.witnesses[x_round].items()):
                    hg.rounds_with_decided_fame.add(x_round)

        # Create cache of undecided and decided events
        ordered_events = []
        for event_id, event in hg.lookup_table.items():
            if event.round_received is None:
                hg.unordered_events.add(event_id)
            else:
                ordered_events.append(event)

        ordered_events = sorted(ordered_events, key=lambda e: (e.round_received, e.consensus_time, e.id))
        hg.ordered_events = [e.id for e in ordered_events]

        bptc.logger.info('Loaded {} events from DB.'.format(len(events)))

        # Create cached account balances
        hg.process_ordered_events()

        return hg
