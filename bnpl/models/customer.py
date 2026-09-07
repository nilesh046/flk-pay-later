class Customer:
    def __init__(self, customer_id, name, credit_limit):
        self.id = customer_id
        self.name = name
        self.credit_limit = credit_limit
        self.outstanding = 0.0
        self.orders = []
        self.blacklisted = False

    def get_available_credit(self):
        return self.credit_limit - self.outstanding

    def can_use_bnpl(self, amount):
        return (not self.blacklisted) and (amount <= self.get_available_credit())

    def apply_bnpl(self, amount):
        if not self.can_use_bnpl(amount):
            raise ValueError("Order exceeds available BNPL credit limit")
        self.outstanding += amount

    def clear_dues(self, amount):
        self.outstanding = max(0.0, self.outstanding - amount)
