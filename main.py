from datetime import date

from bnpl.services.bnpl_service import BNPLService


service = BNPLService()

service.seed_inventory("Shoes 5 200", "Watch 10 1000", "T-Shirt 14 2000")
user = service.register_user("Akshay", 5000)

print("Inventory:")
print(service.view_inventory())

order_id = service.buy(user.id, [("Shoes", 2), ("Watch", 1)], "BNPL", "20-Oct-2021")
print("Order ID:", order_id)
print("Inventory after buy:")
print(service.view_inventory())
print("Dues on 21-Nov-2021:")
print(service.view_dues(user.id, "21-Nov-2021"))

print("Order status:")
print(service.order_status(user.id))
