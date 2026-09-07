class PaymentStrategy:
    def __init__(self, name: str):
        self.name = name

    def apply(self, customer, amount: float) -> None:
        raise NotImplementedError("Subclasses must implement apply()")


class PrepaidStrategy(PaymentStrategy):
    def __init__(self):
        super().__init__("PREPAID")

    def apply(self, customer, amount: float) -> None:
        # prepaid does not affect BNPL outstanding
        return None


class BNPLStrategy(PaymentStrategy):
    def __init__(self):
        super().__init__("BNPL")

    def apply(self, customer, amount: float) -> None:
        if customer.blacklisted:
            raise ValueError("Customer is blacklisted and cannot buy on BNPL")
        if not customer.can_use_bnpl(amount):
            raise ValueError("Order exceeds available BNPL credit limit")
        customer.outstanding += amount
