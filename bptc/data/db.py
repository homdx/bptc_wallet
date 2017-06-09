import sqlite3
from utilities.log_helper import logger
from bptc.data.member import Member
from bptc.data.event import Event
from bptc.data.hashgraph import Hashgraph
from typing import Dict


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
            cls.__connection = sqlite3.connect('data.db')

            # Create tables if necessary
            c = cls.__connection.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS members (verify_key TEXT PRIMARY KEY, signing_key TEXT, head TEXT, stake INT, host TEXT, port INT)')
            c.execute('CREATE TABLE IF NOT EXISTS events (hash TEXT PRIMARY KEY, data TEXT, self_parent TEXT, other_parent TEXT, created_time DATETIME, verify_key TEXT, height INT, signature TEXT)')

        else:
            logger.error("Database has already been connected")

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
        statement = 'INSERT OR REPLACE INTO members VALUES(?, ?, ?, ?, ?, ?)'
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
        statement = 'INSERT OR REPLACE INTO events VALUES(?, ?, ?, ?, ?, ?, ?, ?)'
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
            logger.error("Could not persist object because its type is not supported")

    @classmethod
    def load_hashgraph(cls) -> Hashgraph:
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
        if len(events.items()) > 0:
            hg.add_events(events)

        return hg
