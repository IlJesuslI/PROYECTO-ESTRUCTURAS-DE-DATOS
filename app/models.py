"""Modelos y utilidades de validación para FoodQueue.

Se usan dataclasses para mantener el dominio explícito, pero el almacenamiento
se serializa a diccionarios JSON sencillos.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    """Retorna una fecha ISO-8601 en UTC."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(slots=True)
class Product:
    id: str
    name: str
    price_cop: int
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class OrderItem:
    product_id: str
    name: str
    unit_price_cop: int
    quantity: int

    @property
    def subtotal_cop(self) -> int:
        return self.unit_price_cop * self.quantity

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["subtotal_cop"] = self.subtotal_cop
        return data


@dataclass(slots=True)
class Order:
    id: str
    number: int
    customer: str
    priority: int
    items: list[OrderItem]
    status: str = "pending"
    created_at: str = field(default_factory=utc_now_iso)
    prepared_at: str | None = None

    @property
    def code(self) -> str:
        return f"FQ-{self.number:06d}"

    @property
    def total_cop(self) -> int:
        return sum(item.subtotal_cop for item in self.items)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "number": self.number,
            "code": self.code,
            "customer": self.customer,
            "priority": self.priority,
            "items": [item.to_dict() for item in self.items],
            "status": self.status,
            "created_at": self.created_at,
            "prepared_at": self.prepared_at,
            "total_cop": self.total_cop,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Order":
        items = [
            OrderItem(
                product_id=str(item["product_id"]),
                name=str(item["name"]),
                unit_price_cop=int(item["unit_price_cop"]),
                quantity=int(item["quantity"]),
            )
            for item in data.get("items", [])
        ]
        return cls(
            id=str(data["id"]),
            number=int(data["number"]),
            customer=str(data["customer"]),
            priority=int(data.get("priority", 0)),
            items=items,
            status=str(data.get("status", "pending")),
            created_at=str(data.get("created_at", utc_now_iso())),
            prepared_at=data.get("prepared_at"),
        )
