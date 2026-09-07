from bnpl.strategies.payment_strategy import BNPLStrategy, PaymentStrategy, PrepaidStrategy


class PaymentStrategyFactory:
    _strategies = {
        "PREPAID": PrepaidStrategy,
        "BNPL": BNPLStrategy,
    }

    @staticmethod
    def get_strategy(payment_method: str) -> PaymentStrategy:
        normalized = payment_method.strip().upper()
        if normalized not in PaymentStrategyFactory._strategies:
            raise ValueError("Unsupported payment method")
        return PaymentStrategyFactory._strategies[normalized]()
