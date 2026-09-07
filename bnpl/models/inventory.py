class InventoryItem:
    def __init__(self, name, price, quantity):
        self.name = name
        self.price = price
        self.quantity = quantity


class Inventory:
    def __init__(self):
        self._items = {}

    def add_product(self, name, price, quantity):
        if quantity < 0:
            raise ValueError("Quantity cannot be negative")
        if name in self._items:
            self._items[name].quantity += quantity
            self._items[name].price = price
            return
        self._items[name] = InventoryItem(name, price, quantity)

    def remove_product(self, name, quantity):
        if name not in self._items:
            raise ValueError(f"Product {name} not found")
        if quantity <= 0:
            raise ValueError("Quantity must be positive")
        if self._items[name].quantity < quantity:
            raise ValueError(f"Not enough stock for {name}")
        self._items[name].quantity -= quantity

    def get_product(self, name):
        if name not in self._items:
            raise ValueError(f"Product {name} not found")
        return self._items[name]

    def reserve(self, items):
        for item in items:
            product = self.get_product(item.product_name)
            if product.quantity < item.quantity:
                raise ValueError(f"Insufficient stock for {item.product_name}")
            product.quantity -= item.quantity

    def view_inventory(self):
        return [
            {
                "name": item.name,
                "quantity": item.quantity,
                "price": round(item.price, 2),
            }
            for item in sorted(self._items.values(), key=lambda x: x.name)
        ]
