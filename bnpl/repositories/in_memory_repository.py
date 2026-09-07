from typing import Dict, Generic, TypeVar

T = TypeVar("T")


class InMemoryRepository(Generic[T]):
    def __init__(self):
        self._items: Dict[str, T] = {}

    def save(self, item: T) -> T:
        self._items[item.id] = item
        return item

    def get_by_id(self, item_id: str) -> T:
        if item_id not in self._items:
            raise KeyError(item_id)
        return self._items[item_id]

    def exists(self, item_id: str) -> bool:
        return item_id in self._items
