class Installment:
    def __init__(self, number: int, amount: float):
        self.number = number
        self.amount = amount
        self.paid = False

    def mark_paid(self) -> None:
        self.paid = True
