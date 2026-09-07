from datetime import date
from threading import RLock

from bnpl.factories.payment_strategy_factory import PaymentStrategyFactory
from bnpl.models.customer import Customer
from bnpl.models.installment import Installment
from bnpl.models.inventory import Inventory
from bnpl.models.order import Order, OrderItem
from bnpl.utils.date_utils import parse_date


class BNPLService:
    def __init__(self):
        self.customers = {}
        self.orders = {}
        self.inventory = Inventory()
        self._customer_counter = 0
        self._order_counter = 0
        self._lock = RLock()

    def seed_inventory(self, *entries):
        with self._lock:
            for entry in entries:
                if isinstance(entry, str):
                    parts = entry.strip().split()
                    if len(parts) != 3:
                        raise ValueError(f"Invalid inventory entry: {entry}")
                    name, quantity, price = parts[0], int(parts[1]), float(parts[2])
                    self.inventory.add_product(name, price, quantity)
                elif isinstance(entry, dict):
                    self.inventory.add_product(entry["name"], float(entry["price"]), int(entry.get("quantity", 0)))
                else:
                    raise ValueError("Unsupported inventory entry format")
            return self.view_inventory()

    def view_inventory(self):
        with self._lock:
            return self.inventory.view_inventory()

    def register_customer(self, customer_id, name, credit_limit):
        with self._lock:
            customer = Customer(customer_id, name, float(credit_limit))
            self.customers[customer_id] = customer
            return customer

    def register_user(self, name, credit_limit):
        with self._lock:
            user_id = self._next_customer_id()
            customer = Customer(user_id, name, float(credit_limit))
            self.customers[user_id] = customer
            return customer

    def create_order(self, customer_id, item_name, amount, installments_count):
        with self._lock:
            if installments_count <= 0:
                raise ValueError("Installments count must be positive")

            customer = self._get_customer(customer_id)
            if not customer.can_use_bnpl(amount):
                raise ValueError("Order exceeds customer credit limit")

            order = Order(
                self._next_order_id(),
                customer_id,
                [OrderItem(item_name, 1, amount)],
                "BNPL",
                date.today(),
                amount,
            )

            per_installment = amount / installments_count
            order.installments = [Installment(i + 1, per_installment) for i in range(installments_count)]
            order.installments_count = installments_count
            order.amount = amount

            self.orders[order.id] = order
            customer.apply_bnpl(amount)
            customer.orders.append(order.id)
            return order

    def buy(self, user_id, items, payment_method, date_of_purchase):
        with self._lock:
            customer = self._get_customer(user_id)
            normalized_items = self._normalize_items(items)
            total_amount = sum(item.get_total_price() for item in normalized_items)

            method = payment_method.upper()
            if method not in {"PREPAID", "BNPL"}:
                raise ValueError("Payment method must be PREPAID or BNPL")

            if method == "BNPL":
                if customer.blacklisted:
                    raise ValueError("Customer is blacklisted and cannot buy on BNPL")
                if not customer.can_use_bnpl(total_amount):
                    raise ValueError("Order exceeds available BNPL credit limit")

            strategy = PaymentStrategyFactory.get_strategy(method)
            strategy.apply(customer, total_amount)
            self.inventory.reserve(normalized_items)

            order = Order(
                self._next_order_id(),
                user_id,
                normalized_items,
                method,
                parse_date(date_of_purchase),
                total_amount,
                total_amount if method == "PREPAID" else 0.0,
            )

            self.orders[order.id] = order
            customer.orders.append(order.id)
            return order.id

    def clear_dues(self, user_id, order_ids, date_of_clearing):
        with self._lock:
            customer = self._get_customer(user_id)
            processed = []
            for order_id in order_ids:
                order = self._get_order(order_id)
                if order.customer_id != user_id:
                    raise ValueError(f"Order {order_id} does not belong to user {user_id}")
                if order.payment_method != "BNPL":
                    continue
                if order.get_remaining_amount() <= 0:
                    continue

                amount_to_clear = order.get_remaining_amount()
                order.make_payment(amount_to_clear)
                customer.clear_dues(amount_to_clear)
                processed.append(order_id)

            self._refresh_blacklist_status(customer, parse_date(date_of_clearing))
            return processed

    def view_dues(self, user_id, as_of_date):
        with self._lock:
            customer = self._get_customer(user_id)
            target_date = parse_date(as_of_date)
            dues = []
            for order_id in customer.orders:
                order = self.orders[order_id]
                if order.payment_method != "BNPL" or order.get_remaining_amount() <= 0:
                    continue
                if order.purchase_date > target_date:
                    continue
                dues.append({
                    "order_id": order.id,
                    "purchase_date": order.purchase_date,
                    "pending_amount": round(order.get_remaining_amount(), 2),
                    "due_by": order.get_due_by_date(),
                    "status": "DELAYED" if order.is_delayed(target_date) else "PENDING",
                })
            return sorted(dues, key=lambda d: d["purchase_date"])

    def order_status(self, user_id):
        with self._lock:
            customer = self._get_customer(user_id)
            result = []
            for order_id in customer.orders:
                order = self.orders[order_id]
                result.append({
                    "order_id": order.id,
                    "purchase_date": order.purchase_date,
                    "payment_method": order.payment_method,
                    "total_amount": round(order.total_amount, 2),
                    "pending_amount": round(order.get_remaining_amount(), 2),
                    "status": order.status,
                    "items": [
                        {"name": item.product_name, "quantity": item.quantity, "price": round(item.unit_price, 2)}
                        for item in order.items
                    ],
                })
            return {
                "user_id": customer.id,
                "available_credit": round(customer.get_available_credit(), 2),
                "orders": sorted(result, key=lambda x: x["purchase_date"]),
            }

    def add_inventory(self, name, price, quantity):
        with self._lock:
            self.inventory.add_product(name, price, quantity)
            return self.view_inventory()

    def remove_inventory(self, name, quantity):
        with self._lock:
            self.inventory.remove_product(name, quantity)
            return self.view_inventory()

    def make_payment(self, order_id, amount):
        with self._lock:
            order = self._get_order(order_id)
            customer = self._get_customer(order.customer_id)
            order.make_payment(amount)
            customer.clear_dues(amount)

    def get_order(self, order_id):
        with self._lock:
            return self._get_order(order_id)

    def _get_customer(self, customer_id):
        customer = self.customers.get(customer_id)
        if customer is None:
            raise ValueError("Customer not found")
        return customer

    def _get_order(self, order_id):
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError("Order not found")
        return order

    def _normalize_items(self, items):
        normalized = []
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                name, quantity = item
                product = self.inventory.get_product(name)
                normalized.append(OrderItem(name, int(quantity), product.price))
            elif isinstance(item, dict):
                product = self.inventory.get_product(item["name"])
                normalized.append(OrderItem(item["name"], int(item["quantity"]), product.price))
            else:
                raise ValueError(f"Invalid item format: {item}")
        return normalized

    def _next_customer_id(self):
        self._customer_counter += 1
        return f"U-{self._customer_counter:04d}"

    def _next_order_id(self):
        self._order_counter += 1
        return f"OD-{self._order_counter:04d}"

    def _refresh_blacklist_status(self, customer, as_of_date):
        defaulted = 0
        for order_id in customer.orders:
            order = self.orders[order_id]
            if order.payment_method == "BNPL" and order.get_remaining_amount() > 0 and order.is_delayed(as_of_date):
                defaulted += 1
        customer.blacklisted = defaulted >= 3

    def order_status(self, user_id):
        customer = self._get_customer(user_id)
        ordered = []
        for order_id in customer.orders:
            order = self.orders[order_id]
            ordered.append({
                "order_id": order.id,
                "purchase_date": order.purchase_date,
                "payment_method": order.payment_method,
                "total_amount": round(order.total_amount, 2),
                "pending_amount": round(order.get_remaining_amount(), 2),
                "status": order.status,
                "items": [
                    {
                        "name": item.product_name,
                        "quantity": item.quantity,
                        "price": round(item.unit_price, 2),
                    }
                    for item in order.items
                ],
            })

        return {
            "user_id": customer.id,
            "available_credit": round(customer.get_available_credit(), 2),
            "orders": sorted(ordered, key=lambda item: item["purchase_date"]),
        }

    def add_inventory(self, name, price, quantity):
        self.inventory.add_product(name, price, quantity)
        return self.view_inventory()

    def remove_inventory(self, name, quantity):
        self.inventory.remove_product(name, quantity)
        return self.view_inventory()

    def _get_customer(self, user_id):
        customer = self.customers.get(user_id)
        if customer is None:
            raise ValueError("Customer not found")
        return customer

    def make_payment(self, order_id, amount):
        order = self._get_order(order_id)
        customer = self._get_customer(order.customer_id)
        order.apply_payment(amount)
        customer.clear_dues(amount)

    def get_order(self, order_id):
        return self._get_order(order_id)

    def _get_order(self, order_id):
        order = self.orders.get(order_id)
        if order is None:
            raise ValueError("Order not found")
        return order

    def _is_blacklisted(self, customer):
        defaulted_orders = 0
        for order_id in customer.orders:
            order = self.orders[order_id]
            if order.payment_method == "BNPL" and order.get_remaining_amount() > 0 and order.is_delayed(date.today()):
                defaulted_orders += 1
        customer.blacklisted = defaulted_orders >= 3
        return customer.blacklisted

    def _refresh_blacklist_status(self, customer, as_of_date):
        defaulted_orders = 0
        for order_id in customer.orders:
            order = self.orders[order_id]
            if order.payment_method == "BNPL" and order.get_remaining_amount() > 0 and order.is_delayed(as_of_date):
                defaulted_orders += 1
        customer.blacklisted = defaulted_orders >= 3

    def _normalize_items(self, items):
        normalized = []
        for item in items:
            if isinstance(item, tuple) and len(item) == 2:
                product_name, quantity = item
                product = self.inventory.get_product(product_name)
                normalized.append(OrderItem(product_name, int(quantity), product.price))
            elif isinstance(item, dict):
                product_name = item["name"]
                quantity = int(item["quantity"])
                product = self.inventory.get_product(product_name)
                normalized.append(OrderItem(product_name, quantity, product.price))
            else:
                raise ValueError(f"Invalid item format: {item}")
        return normalized

    def _next_customer_id(self):
        self._customer_counter += 1
        return f"U-{self._customer_counter:04d}"

    def _next_order_id(self):
        self._order_counter += 1
        return f"OD-{self._order_counter:04d}"
