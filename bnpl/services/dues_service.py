from datetime import date


class DuesService:
    def __init__(self, customers, orders):
        self.customers = customers
        self.orders = orders

    def get_dues(self, user_id: str, as_of_date):
        customer = self.customers[user_id]
        dues = []
        for order_id in customer.orders:
            order = self.orders[order_id]
            if order.payment_method == "BNPL" and order.get_remaining_amount() > 0:
                dues.append({
                    "order_id": order.id,
                    "purchase_date": order.purchase_date,
                    "pending_amount": order.get_remaining_amount(),
                    "status": "DELAYED" if order.is_delayed(as_of_date) else "PENDING",
                })
        return sorted(dues, key=lambda d: d["purchase_date"])
