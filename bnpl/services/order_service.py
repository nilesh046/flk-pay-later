from threading import RLock
from datetime import date

from bnpl.factories.payment_strategy_factory import PaymentStrategyFactory
from bnpl.models.order import Order, OrderItem


class OrderService:
    def __init__(self, inventory, customers, orders):
        self.inventory = inventory
        self.customers = customers
        self.orders = orders
        self.lock = RLock()

    def place_order(self, user_id: str, items, payment_method: str, purchase_date):
        with self.lock:
            customer = self.customers[user_id]
            normalized = self._normalize_items(items)
            total_amount = sum(item.quantity * item.unit_price for item in normalized)

            strategy = PaymentStrategyFactory.get_strategy(payment_method)
            strategy.apply(customer, total_amount)

            for item in normalized:
                self.inventory.get_product(item.product_name).quantity -= item.quantity

            order_id = f"OD-{len(self.orders) + 1:04d}"
            order = Order(
                id=order_id,
                customer_id=user_id,
                items=normalized,
                payment_method=payment_method.upper(),
                purchase_date=purchase_date,
                total_amount=total_amount,
                paid_amount=0.0 if payment_method.upper() == "BNPL" else total_amount,
                status="PLACED",
            )
            self.orders[order_id] = order
            customer.orders.append(order_id)
            return order

    def _normalize_items(self, items):
        normalized = []
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                name, qty = item
                product = self.inventory.get_product(name)
                normalized.append(OrderItem(name, qty, product.price))
            else:
                raise ValueError("Invalid item format")
        return normalized
