from collections import OrderedDict
from typing import Dict
import bptc


class TransactionStatus:
    UNCONFIRMED = 0
    CONFIRMED = 1
    DENIED = 2

    @classmethod
    def text_for_value(cls, value):
        return ['Unconfirmed', 'Confirmed', 'Denied'][value]


class Transaction:

    def __init__(self, receiver, amount, comment=""):
        self.receiver = receiver
        self.amount = amount
        self.comment = comment
        self.status = TransactionStatus.UNCONFIRMED

    def __str__(self):
        return "Transaction(receiver={}, amount={}, comment={})".format(self.receiver, self.amount, self.comment)

    def __repr__(self):
        return self.__str__()

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('receiver', self.receiver),
            ('amount', self.amount)])

    @classmethod
    def from_dict(cls, transaction_dict):
        if transaction_dict['type'] == 'money':
            return MoneyTransaction(transaction_dict['receiver'],
                                    transaction_dict['amount'],
                                    transaction_dict['comment'] if 'comment' in transaction_dict else "")
        elif transaction_dict['type'] == 'stake':
            return StakeTransaction(transaction_dict['receiver'],
                                    transaction_dict['amount'],
                                    transaction_dict['comment'] if 'comment' in transaction_dict else "")
        else:
            bptc.logger.error("Received invalid transaction type: {}".format(transaction_dict['type']))
            return None


class MoneyTransaction(Transaction):

    def __str__(self):
        return "MoneyTransaction(receiver={}, amount={}, comment={})".format(self.receiver, self.amount, self.comment)

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('type', 'money'),
            ('receiver', self.receiver),
            ('amount', self.amount),
            ('comment', self.comment)])


class StakeTransaction(Transaction):

    def __str__(self):
        return "StakeTransaction(receiver={}, amount={}, comment={})".format(self.receiver, self.amount, self.comment)

    def to_dict(self) -> Dict:
        return OrderedDict([
            ('type', 'stake'),
            ('receiver', self.receiver),
            ('amount', self.amount),
            ('comment', self.comment)])
