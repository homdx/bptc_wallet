import sqlite3
from utilities.log_helper import logger
from hptaler.data.member import Member
from hptaler.data.hashgraph import Hashgraph
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

        else:
            logger.error("Database has already been connected")

    @classmethod
    def __get_cursor(cls) -> sqlite3:
        # Connect to DB on first call
        if cls.__connection is None:
            cls.__connect()
        return cls.__connection.cursor()

    @classmethod
    def __save_member(cls, m) -> None:
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
    def save(cls, obj) -> None:
        """
        Saves an object to the database
        :param obj: A Member object
        :return: None
        """
        if isinstance(obj, Member):
            cls.__save_member(obj)
        if isinstance(obj, Hashgraph):
            cls.__save_member(obj.me)
            for _, member in obj.known_members.items():
                cls.__save_member(member)
        else:
            logger.error("Could not persist object because its type is not supported")

    @classmethod
    def load_hashgraph(cls) -> Hashgraph:
        c = cls.__get_cursor()

        # Load members
        me: Member = None
        members: Dict[str, Member] = dict()

        for row in c.execute('SELECT * FROM members'):
            if row[1] is not None:
                me = Member.from_db_tuple(row)
            else:
                members[row[0]] = Member.from_db_tuple(row)

        hg: Hashgraph = Hashgraph(me)
        hg.known_members = members

        return hg
