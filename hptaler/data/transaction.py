class Transaction:

    def __init__(self, receiver, amount):
        self.receiver = receiver
        self.amount = amount

    def __str__(self):
        return "Transaction(receiver={}, amount={})".format(self.receiver, self.amount)

    def to_dict(self):
        return dict(
            receiver=self.receiver,
            amount=self.amount
        )

    @classmethod
    def from_dict(cls, transaction_dict):
        return Transaction(transaction_dict['receiver'], transaction_dict['amount'])

