from bnpl.models.inventory import Inventory


class InventoryBuilder:
    def __init__(self):
        self._inventory = Inventory()

    def add_item(self, name: str, price: float, quantity: int):
        self._inventory.add_product(name, price, quantity)
        return self

    def from_entries(self, entries):
        for entry in entries:
            parts = entry.strip().split()
            if len(parts) != 3:
                raise ValueError(f"Invalid inventory entry: {entry}")
            name, quantity, price = parts[0], int(parts[1]), float(parts[2])
            self.add_item(name, price, quantity)
        return self

    def build(self):
        return self._inventory
