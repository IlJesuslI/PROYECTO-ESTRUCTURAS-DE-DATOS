"""Lógica principal de FoodQueue y uso explícito de estructuras lineales.

Estructuras integradas:
1. Arreglo dinámico (list): self.products.
2. Cola FIFO (collections.deque): self.normal_queue.
3. Cola con prioridad (heapq): self.priority_queue.
4. Pila LIFO (list): self.prepared_stack.

También se usan diccionarios como índices auxiliares O(1); no sustituyen las
estructuras lineales, sino que evitan búsquedas innecesarias por identificador.
"""

from __future__ import annotations

import heapq
import json
import os
import threading
import uuid
from collections import deque
from pathlib import Path
from typing import Any

from .models import Order, OrderItem, Product, utc_now_iso


class ValidationError(ValueError):
    """Error de datos de entrada controlado por la API."""


class NotFoundError(LookupError):
    """Recurso solicitado inexistente."""


class ConflictError(RuntimeError):
    """Operación incompatible con el estado actual."""


class FoodQueueService:
    """Servicio de dominio seguro para uso concurrente dentro de un proceso."""

    MAX_NAME = 80
    MAX_CUSTOMER = 80
    MAX_PRODUCT_PRICE = 50_000_000
    MAX_DISTINCT_ITEMS = 50
    MAX_UNITS_PER_LINE = 99
    MAX_TOTAL_UNITS = 500
    MAX_CONSECUTIVE_PRIORITY = 3

    def __init__(self, state_path: str | Path):
        self.state_path = Path(state_path)
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()

        # ARREGLO DINÁMICO: catálogo ordenado de productos.
        self.products: list[Product] = []
        self._product_index: dict[str, Product] = {}

        # COLA FIFO: pedidos con prioridad normal (primero en entrar, primero en salir).
        self.normal_queue: deque[str] = deque()

        # COLA CON PRIORIDAD: tuplas (-prioridad, número_secuencial, id_pedido).
        self.priority_queue: list[tuple[int, int, str]] = []

        # PILA LIFO: último pedido preparado queda al tope para permitir deshacer.
        self.prepared_stack: list[str] = []

        self.orders: dict[str, Order] = {}
        self.next_order_number = 1
        self._consecutive_priority = 0
        self._load()

    # ---------- Persistencia ----------
    def _load(self) -> None:
        """Carga el estado persistido y reconstruye las estructuras lineales."""
        if not self.state_path.exists():
            self._seed_demo_menu()
            self._persist()
            return

        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            raise RuntimeError(
                f"No se pudo leer el archivo de estado: {self.state_path}. "
                "Revise que el JSON no esté corrupto."
            ) from exc

        self.products = [
            Product(
                id=str(item["id"]),
                name=str(item["name"]),
                price_cop=int(item["price_cop"]),
                active=bool(item.get("active", True)),
            )
            for item in data.get("products", [])
        ]
        self._rebuild_product_index()

        self.orders = {}
        for raw in data.get("orders", []):
            order = Order.from_dict(raw)
            self.orders[order.id] = order

        self.next_order_number = int(data.get("next_order_number", 1))
        self._consecutive_priority = int(data.get("consecutive_priority", 0))

        # Desde v2 se conserva el orden exacto de las estructuras para que un
        # reinicio no cambie el turno de un pedido reencolado ni el tope LIFO.
        if int(data.get("version", 1)) >= 2:
            self.normal_queue = deque(
                oid for oid in data.get("normal_queue", [])
                if oid in self.orders and self.orders[oid].status == "pending"
            )
            self.priority_queue = [
                (int(entry[0]), int(entry[1]), str(entry[2]))
                for entry in data.get("priority_queue", [])
                if len(entry) == 3
                and str(entry[2]) in self.orders
                and self.orders[str(entry[2])].status == "pending"
            ]
            heapq.heapify(self.priority_queue)
            self.prepared_stack = [
                oid for oid in data.get("prepared_stack", [])
                if oid in self.orders and self.orders[oid].status == "prepared"
            ]
        else:
            self._rebuild_order_structures()

    def _persist(self) -> None:
        """Guarda todo el estado con reemplazo atómico para evitar JSON parcial."""
        # Solo se persisten IDs válidos en las estructuras; así se compactan las
        # entradas obsoletas producidas por cancelación perezosa.
        valid_normal = [
            oid for oid in self.normal_queue
            if oid in self.orders and self.orders[oid].status == "pending"
        ]
        valid_priority = [
            [neg_priority, sequence, oid]
            for neg_priority, sequence, oid in self.priority_queue
            if oid in self.orders and self.orders[oid].status == "pending"
        ]
        valid_stack = [
            oid for oid in self.prepared_stack
            if oid in self.orders and self.orders[oid].status == "prepared"
        ]

        payload = {
            "version": 2,
            "next_order_number": self.next_order_number,
            "consecutive_priority": self._consecutive_priority,
            "products": [p.to_dict() for p in self.products],
            "orders": [o.to_dict() for o in self.orders.values()],
            "normal_queue": valid_normal,
            "priority_queue": valid_priority,
            "prepared_stack": valid_stack,
        }
        temp_path = self.state_path.with_suffix(self.state_path.suffix + ".tmp")
        temp_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        os.replace(temp_path, self.state_path)

    def _seed_demo_menu(self) -> None:
        for name, price in (
            ("Hamburguesa clásica", 18000),
            ("Pizza personal", 16000),
            ("Papas francesas", 8000),
            ("Limonada", 6000),
        ):
            product = Product(id=str(uuid.uuid4()), name=name, price_cop=price)
            self.products.append(product)
        self._rebuild_product_index()

    def _rebuild_product_index(self) -> None:
        self._product_index = {p.id: p for p in self.products}

    def _rebuild_order_structures(self) -> None:
        self.normal_queue.clear()
        self.priority_queue.clear()
        self.prepared_stack.clear()

        ordered = sorted(self.orders.values(), key=lambda order: order.number)
        for order in ordered:
            if order.status == "pending":
                self._enqueue_order(order)
            elif order.status == "prepared":
                self.prepared_stack.append(order.id)

    # ---------- Utilidades de validación ----------
    @staticmethod
    def _clean_text(value: Any, field: str, max_len: int) -> str:
        if not isinstance(value, str):
            raise ValidationError(f"{field} debe ser texto.")
        cleaned = " ".join(value.strip().split())
        if not cleaned:
            raise ValidationError(f"{field} no puede estar vacío.")
        if len(cleaned) > max_len:
            raise ValidationError(f"{field} no puede superar {max_len} caracteres.")
        # Evita caracteres de control; HTML se renderiza usando textContent en JS.
        if any(ord(ch) < 32 for ch in cleaned):
            raise ValidationError(f"{field} contiene caracteres de control no permitidos.")
        return cleaned

    @staticmethod
    def _parse_int(value: Any, field: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool):
            raise ValidationError(f"{field} debe ser un número entero.")
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{field} debe ser un número entero.") from exc
        if str(value).strip() not in {str(number), f"+{number}"} and not isinstance(value, int):
            # Evita aceptar silenciosamente 2.7 como 2 o textos ambiguos.
            try:
                if float(value) != number:
                    raise ValidationError(f"{field} debe ser un número entero.")
            except (TypeError, ValueError):
                raise ValidationError(f"{field} debe ser un número entero.")
        if not minimum <= number <= maximum:
            raise ValidationError(f"{field} debe estar entre {minimum} y {maximum}.")
        return number

    # ---------- Productos / arreglo dinámico ----------
    def list_products(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            products = self.products if include_inactive else [p for p in self.products if p.active]
            return [p.to_dict() for p in products]

    def add_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            name = self._clean_text(payload.get("name"), "Nombre", self.MAX_NAME)
            price = self._parse_int(payload.get("price_cop"), "Precio", 1, self.MAX_PRODUCT_PRICE)

            if any(p.active and p.name.casefold() == name.casefold() for p in self.products):
                raise ConflictError("Ya existe un producto activo con ese nombre.")

            product = Product(id=str(uuid.uuid4()), name=name, price_cop=price)
            self.products.append(product)  # append amortizado O(1)
            self._product_index[product.id] = product
            self._persist()
            return product.to_dict()

    def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            product = self._product_index.get(product_id)
            if product is None:
                raise NotFoundError("Producto no encontrado.")

            name = self._clean_text(payload.get("name", product.name), "Nombre", self.MAX_NAME)
            price = self._parse_int(
                payload.get("price_cop", product.price_cop), "Precio", 1, self.MAX_PRODUCT_PRICE
            )
            active = payload.get("active", product.active)
            if not isinstance(active, bool):
                raise ValidationError("active debe ser verdadero o falso.")

            if any(
                p.id != product.id and p.active and p.name.casefold() == name.casefold()
                for p in self.products
            ):
                raise ConflictError("Ya existe otro producto activo con ese nombre.")

            product.name = name
            product.price_cop = price
            product.active = active
            self._persist()
            return product.to_dict()

    def deactivate_product(self, product_id: str) -> dict[str, Any]:
        """Borrado lógico: conserva pedidos históricos que referencian el producto."""
        with self._lock:
            product = self._product_index.get(product_id)
            if product is None:
                raise NotFoundError("Producto no encontrado.")
            product.active = False
            self._persist()
            return product.to_dict()

    # ---------- Pedidos / colas ----------
    def _enqueue_order(self, order: Order) -> None:
        if order.priority <= 0:
            self.normal_queue.append(order.id)
        else:
            heapq.heappush(self.priority_queue, (-order.priority, order.number, order.id))

    def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            customer = self._clean_text(payload.get("customer"), "Cliente", self.MAX_CUSTOMER)
            priority = self._parse_int(payload.get("priority", 0), "Prioridad", 0, 2)
            raw_items = payload.get("items")
            if not isinstance(raw_items, list) or not raw_items:
                raise ValidationError("El pedido debe contener al menos un producto.")
            if len(raw_items) > self.MAX_DISTINCT_ITEMS:
                raise ValidationError(
                    f"Un pedido no puede superar {self.MAX_DISTINCT_ITEMS} líneas de producto."
                )

            merged: dict[str, int] = {}
            for raw in raw_items:
                if not isinstance(raw, dict):
                    raise ValidationError("Cada elemento del pedido debe ser un objeto.")
                product_id = str(raw.get("product_id", ""))
                qty = self._parse_int(
                    raw.get("quantity"), "Cantidad", 1, self.MAX_UNITS_PER_LINE
                )
                merged[product_id] = merged.get(product_id, 0) + qty

            if sum(merged.values()) > self.MAX_TOTAL_UNITS:
                raise ValidationError(
                    f"El pedido no puede superar {self.MAX_TOTAL_UNITS} unidades en total."
                )

            items: list[OrderItem] = []
            for product_id, qty in merged.items():
                if qty > self.MAX_UNITS_PER_LINE:
                    raise ValidationError(
                        f"La cantidad acumulada de un producto no puede superar {self.MAX_UNITS_PER_LINE}."
                    )
                product = self._product_index.get(product_id)
                if product is None or not product.active:
                    raise ValidationError("Uno de los productos no existe o ya no está activo.")
                items.append(
                    OrderItem(
                        product_id=product.id,
                        name=product.name,
                        unit_price_cop=product.price_cop,
                        quantity=qty,
                    )
                )

            order = Order(
                id=str(uuid.uuid4()),
                number=self.next_order_number,
                customer=customer,
                priority=priority,
                items=items,
            )
            self.next_order_number += 1
            self.orders[order.id] = order
            self._enqueue_order(order)
            self._persist()
            return order.to_dict()

    def _pop_valid_normal(self) -> Order | None:
        while self.normal_queue:
            order_id = self.normal_queue.popleft()
            order = self.orders.get(order_id)
            if order and order.status == "pending":
                return order
        return None

    def _pop_valid_priority(self) -> Order | None:
        while self.priority_queue:
            _negative_priority, _sequence, order_id = heapq.heappop(self.priority_queue)
            order = self.orders.get(order_id)
            if order and order.status == "pending":
                return order
        return None

    def process_next_order(self) -> dict[str, Any]:
        """Prepara el siguiente pedido, evitando inanición de la cola normal.

        Hasta tres pedidos prioritarios pueden adelantarse consecutivamente. Si hay
        pedidos normales esperando, el cuarto turno corresponde a la cola FIFO.
        """
        with self._lock:
            normal_available = any(
                self.orders.get(oid) and self.orders[oid].status == "pending"
                for oid in self.normal_queue
            )
            priority_available = bool(self.priority_queue)

            order: Order | None = None
            if priority_available and (
                self._consecutive_priority < self.MAX_CONSECUTIVE_PRIORITY
                or not normal_available
            ):
                order = self._pop_valid_priority()
                if order:
                    self._consecutive_priority += 1

            if order is None and normal_available:
                order = self._pop_valid_normal()
                if order:
                    self._consecutive_priority = 0

            if order is None and priority_available:
                order = self._pop_valid_priority()
                if order:
                    self._consecutive_priority += 1

            if order is None:
                raise NotFoundError("No hay pedidos pendientes para preparar.")

            order.status = "prepared"
            order.prepared_at = utc_now_iso()
            self.prepared_stack.append(order.id)  # push LIFO
            self._persist()
            return order.to_dict()

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancela un pedido pendiente; entradas obsoletas se ignoran al desencolar."""
        with self._lock:
            order = self.orders.get(order_id)
            if order is None:
                raise NotFoundError("Pedido no encontrado.")
            if order.status != "pending":
                raise ConflictError("Solo se pueden cancelar pedidos pendientes.")
            order.status = "cancelled"
            self._persist()
            return order.to_dict()

    def undo_last_prepared(self) -> dict[str, Any]:
        """Pop de la pila y reencolado del último pedido preparado."""
        with self._lock:
            while self.prepared_stack:
                order_id = self.prepared_stack.pop()
                order = self.orders.get(order_id)
                if order and order.status == "prepared":
                    order.status = "pending"
                    order.prepared_at = None
                    self._enqueue_order(order)
                    self._persist()
                    return order.to_dict()
            raise NotFoundError("No hay pedidos preparados para deshacer.")

    def list_pending_orders(self) -> list[dict[str, Any]]:
        """Vista ordenada según la política real de atención, sin mutar las colas."""
        with self._lock:
            priority_orders = sorted(
                (o for o in self.orders.values() if o.status == "pending" and o.priority > 0),
                key=lambda o: (-o.priority, o.number),
            )
            normal_orders = sorted(
                (o for o in self.orders.values() if o.status == "pending" and o.priority <= 0),
                key=lambda o: o.number,
            )
            return [o.to_dict() for o in priority_orders + normal_orders]

    def list_history(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            limit = max(1, min(int(limit), 500))
            ids = reversed(self.prepared_stack[-limit:])
            return [self.orders[oid].to_dict() for oid in ids if oid in self.orders]

    def status(self) -> dict[str, Any]:
        with self._lock:
            pending = sum(1 for o in self.orders.values() if o.status == "pending")
            prepared = sum(1 for o in self.orders.values() if o.status == "prepared")
            cancelled = sum(1 for o in self.orders.values() if o.status == "cancelled")
            return {
                "products_active": sum(1 for p in self.products if p.active),
                "orders_pending": pending,
                "orders_prepared": prepared,
                "orders_cancelled": cancelled,
                "normal_queue_size": sum(
                    1
                    for oid in self.normal_queue
                    if oid in self.orders and self.orders[oid].status == "pending"
                ),
                "priority_queue_size": sum(
                    1
                    for _p, _n, oid in self.priority_queue
                    if oid in self.orders and self.orders[oid].status == "pending"
                ),
                "stack_size": len(self.prepared_stack),
            }
