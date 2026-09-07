from datetime import timedelta

from bnpl.models.installment import Installment


class OrderItem:
    def __init__(self, product_name, quantity, unit_price):
        self.product_name = product_name
        self.quantity = quantity
        self.unit_price = unit_price

    def get_total_price(self):
        return self.quantity * self.unit_price


class Order:
    def __init__(self, order_id, customer_id, items, payment_method, purchase_date, total_amount, paid_amount=0.0):
        self.id = order_id
        self.customer_id = customer_id
        self.items = items
        self.payment_method = payment_method
        self.purchase_date = purchase_date
        self.total_amount = total_amount
        self.paid_amount = paid_amount
        self.status = "PLACED"
        self.amount = total_amount
        self.installments = []
        self.installments_count = 0

    def get_remaining_amount(self):
        return self.total_amount - self.paid_amount

    def get_due_by_date(self):
        return self.purchase_date + timedelta(days=30)

    def make_payment(self, amount):
        if amount <= 0:
            raise ValueError("Payment amount must be positive")
        if amount > self.get_remaining_amount():
            raise ValueError("Payment exceeds pending amount")
        self.paid_amount += amount
        if self.get_remaining_amount() == 0:
            self.status = "PAID"

    def apply_payment(self, amount):
        self.make_payment(amount)

    @property
    def remaining_amount(self):
        return self.get_remaining_amount()

    def is_delayed(self, as_of_date):
        return self.get_remaining_amount() > 0 and as_of_date > self.get_due_by_date()

    def mark_installments_paid(self, amount):
        remaining = amount
        for installment in self.installments:
            if installment.paid:
                continue
            if remaining >= installment.amount:
                installment.mark_paid()
                remaining -= installment.amount
        if remaining > 0:
            raise ValueError("Could not allocate payment across installments")
