"""FoodQueue: catálogo dinámico, dos colas sobre arreglos y pila histórica.

Encolado / extracción: O(1) amortizado, sin recorrer toda la cola.
Persistencia incremental: JSON Lines (JSONL); sin SQLite.
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any

from .models import Order, OrderItem, Product, utc_now_iso


class ValidationError(ValueError):
    """Datos inválidos recibidos de la interfaz."""


class NotFoundError(LookupError):
    """Identificador o recurso inexistente."""


class ConflictError(RuntimeError):
    """Acción incompatible con el estado del pedido."""


class ArrayQueue:
    """Cola FIFO implementada con arreglo dinámico e índice de cabeza.

    Al sacar se avanza ``head`` sin ejecutar list.pop(0), que costaría O(n).
    Las entradas canceladas se descartan perezosamente al llegar a la cabeza.
    Compactación cuando la mitad del buffer ya se consumió: amortiza a O(1).
    """

    def __init__(self, values=()):
        self.items: list[Order] = list(values)
        self.head: int = 0

    def push(self, order: Order) -> None:
        self.items.append(order)

    def pop(self) -> Order | None:
        while self.head < len(self.items):
            order = self.items[self.head]
            self.head += 1
            if order.status == "pending":
                self._compact()
                return order
        self._compact()
        return None

    def _compact(self) -> None:
        if self.head and self.head * 2 >= len(self.items):
            self.items = self.items[self.head:]
            self.head = 0

    def __len__(self) -> int:
        return len(self.items) - self.head  # incluye cancelados hasta que avancen


class FoodQueueService:
    """Dominio y persistencia. Un RLock protege un proceso del servidor HTTP."""

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
        self.log_path = self.state_path.with_suffix('.jsonl')
        self._lock = threading.RLock()
        self.products: list[Product] = []          # arreglo dinámico
        self._product_index: dict[str, Product] = {}
        self.orders: dict[str, Order] = {}         # índice auxiliar por ID
        self.normal_queue = ArrayQueue()           # cola FIFO sobre arreglo
        self.high_queue = ArrayQueue()             # cola prioritaria sobre arreglo
        self.prepared_stack: list[str] = []         # pila LIFO / historial
        self.next_order_number = 1
        self._consecutive_priority = 0
        self._queue_counter = 0
        self._stack_counter = 0
        self._queue_positions: dict[str, int] = {}
        self._stack_positions: dict[str, int] = {}
        self._counts = {'normal': 0, 'high': 0, 'prepared': 0, 'cancelled': 0}
        self._load()

    # ----- Inicialización y migración -----
    def _seed_demo_menu(self) -> None:
        for name, price in (("Hamburguesa clásica", 18000), ("Pizza personal", 16000),
                            ("Papas francesas", 8000), ("Limonada", 6000)):
            self.products.append(Product(id=str(uuid.uuid4()), name=name, price_cop=price))
        self._rebuild_product_index()

    def _rebuild_product_index(self) -> None:
        self._product_index = {p.id: p for p in self.products}

    def _load_legacy_json(self) -> None:
        data = json.loads(self.state_path.read_text(encoding='utf-8'))
        self.products = [Product(id=str(p['id']), name=str(p['name']),
                         price_cop=int(p['price_cop']), active=bool(p.get('active', True)))
                         for p in data.get('products', [])]
        self._rebuild_product_index()
        for raw in data.get('orders', []):
            order = Order.from_dict(raw)
            order.priority = 1 if order.priority > 0 else 0
            self.orders[order.id] = order
        self.next_order_number = max(int(data.get('next_order_number', 1)),
                                     max((o.number for o in self.orders.values()), default=0) + 1)
        self._consecutive_priority = min(self.MAX_CONSECUTIVE_PRIORITY,
                                         int(data.get('consecutive_priority', 0)))
        version = int(data.get('version', 1))
        if version >= 2:
            normal_ids = [oid for oid in data.get('normal_queue', [])
                          if oid in self.orders and self.orders[oid].status == 'pending'
                          and self.orders[oid].priority == 0]
            # Originalmente había dos niveles superiores en heap; ahora todos son 'alta'.
            old_priority_ids = [str(entry[2]) for entry in data.get('priority_queue', [])
                                if len(entry) == 3 and str(entry[2]) in self.orders
                                and self.orders[str(entry[2])].status == 'pending']
            high_ids = sorted(set(old_priority_ids + [oid for oid in data.get('high_queue', []) if oid in self.orders]), key=lambda oid: self.orders[oid].number)
            stack_ids = [oid for oid in data.get('prepared_stack', [])
                         if oid in self.orders and self.orders[oid].status == 'prepared']
        else:
            normal_ids = sorted((o.id for o in self.orders.values()
                                 if o.status == 'pending' and o.priority == 0),
                                key=lambda oid: self.orders[oid].number)
            high_ids = sorted((o.id for o in self.orders.values()
                               if o.status == 'pending' and o.priority == 1),
                              key=lambda oid: self.orders[oid].number)
            stack_ids = sorted((o.id for o in self.orders.values() if o.status == 'prepared'),
                               key=lambda oid: self.orders[oid].number)
        # Recupera pedidos si un archivo legado enumera colas incompletas.
        pending_seen = set(normal_ids + high_ids)
        for o in sorted(self.orders.values(), key=lambda x: x.number):
            if o.status == 'pending' and o.id not in pending_seen:
                (high_ids if o.priority else normal_ids).append(o.id)
        self.normal_queue = ArrayQueue(self.orders[oid] for oid in normal_ids)
        self.high_queue = ArrayQueue(self.orders[oid] for oid in high_ids)
        self.prepared_stack = stack_ids
        for oid in normal_ids + high_ids:
            self._queue_counter += 1
            self._queue_positions[oid] = self._queue_counter
        for oid in stack_ids:
            self._stack_counter += 1
            self._stack_positions[oid] = self._stack_counter
        self._calculate_counts()

    def _load(self) -> None:
        """Carga instantánea inicial + reproduce el diario incremental JSONL.

        No abre bases SQL. Si hay un JSON legado, respeta el orden de sus colas.
        El diario puede crecer; la reconstrucción de arranque es O(n + e).
        """
        if self.state_path.exists():
            self._load_legacy_json()
        else:
            if self.state_path.with_suffix('.sqlite3').exists():
                raise RuntimeError('Se encontró una base de datos anterior. Haz una copia y exporta los pedidos a JSON antes de iniciar la versión JSONL; no se creará un menú vacío sobre datos existentes.')
            self._seed_demo_menu()
            self._snapshot()
        if self.log_path.exists():
            with self.log_path.open('r', encoding='utf-8') as stream:
                for line in stream:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                    except json.JSONDecodeError:
                        # Una última línea truncada tras apagado se ignora.
                        break
                    action = event['action']
                    if action == 'product':
                        product = Product(**event['product'])
                        if product.id not in self._product_index:
                            self.products.append(product)
                        else:
                            for idx, current in enumerate(self.products):
                                if current.id == product.id:
                                    self.products[idx] = product
                                    break
                        self._product_index[product.id] = product
                    elif action == 'order':
                        order = Order.from_dict(event['order'])
                        order.priority = 1 if order.priority > 0 else 0
                        self.orders[order.id] = order
                        if order.status == 'pending':
                            self._queue_positions[order.id] = int(event['queue_seq'])
                        elif order.status == 'prepared':
                            self._queue_positions.pop(order.id, None)
                            self._stack_positions[order.id] = int(event['stack_seq'])
                        else:
                            self._queue_positions.pop(order.id, None)
                    elif action == 'delete':
                        oid = event['id']
                        self.orders.pop(oid, None)
                        self._queue_positions.pop(oid, None)
                        self._stack_positions.pop(oid, None)
                    elif action == 'clear':
                        for oid, order in list(self.orders.items()):
                            if order.status == 'prepared':
                                del self.orders[oid]
                                self._stack_positions.pop(oid, None)
                    self.next_order_number = max(self.next_order_number, int(event.get('next_order_number', 1)))
                    self._consecutive_priority = int(event.get('consecutive_priority', 0))
                    self._queue_counter = max(self._queue_counter, int(event.get('queue_counter', 0)))
                    self._stack_counter = max(self._stack_counter, int(event.get('stack_counter', 0)))
        # La reconstrucción usa índices de orden, sin ordenar cada vez que se atiende.
        pending = [o for o in self.orders.values() if o.status == 'pending']
        normal = sorted((o for o in pending if o.priority == 0),
                        key=lambda o: (self._queue_positions.get(o.id, o.number), o.number))
        high = sorted((o for o in pending if o.priority == 1),
                      key=lambda o: (self._queue_positions.get(o.id, o.number), o.number))
        self.normal_queue = ArrayQueue(normal)
        self.high_queue = ArrayQueue(high)
        self.prepared_stack = [o.id for o in sorted(
            (o for o in self.orders.values() if o.status == 'prepared'),
            key=lambda o: (self._stack_positions.get(o.id, o.number), o.number))]
        self._queue_counter = max(self._queue_counter, max(self._queue_positions.values(), default=0))
        self._stack_counter = max(self._stack_counter, max(self._stack_positions.values(), default=0))
        self.next_order_number = max(self.next_order_number,
                                     max((o.number for o in self.orders.values()), default=0) + 1)
        self._calculate_counts()

    def _calculate_counts(self) -> None:
        self._counts = {'normal': 0, 'high': 0, 'prepared': 0, 'cancelled': 0}
        for order in self.orders.values():
            if order.status == 'pending':
                self._counts['high' if order.priority else 'normal'] += 1
            elif order.status in self._counts:
                self._counts[order.status] += 1

    def _snapshot(self) -> None:
        """Crea el estado base una sola vez; no se reescribe por pedido."""
        state = {'version': 3, 'products': [p.to_dict() for p in self.products],
                 'orders': [o.to_dict() for o in self.orders.values()],
                 'normal_queue': [o.id for o in self.normal_queue.items[self.normal_queue.head:]
                                  if o.status == 'pending'],
                 'high_queue': [o.id for o in self.high_queue.items[self.high_queue.head:]
                                if o.status == 'pending'],
                 'prepared_stack': [oid for oid in self.prepared_stack if oid in self.orders],
                 'next_order_number': self.next_order_number,
                 'consecutive_priority': self._consecutive_priority}
        temp = self.state_path.with_suffix('.json.tmp')
        temp.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        os.replace(temp, self.state_path)

    def _append_event(self, event: dict[str, Any]) -> None:
        event.update(next_order_number=self.next_order_number,
                     consecutive_priority=self._consecutive_priority,
                     queue_counter=self._queue_counter, stack_counter=self._stack_counter)
        with self.log_path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False, separators=(',', ':')) + '\n')

    def _persist(self, *, order: Order | None = None, product: Product | None = None) -> None:
        if order is not None:
            self._append_event({'action': 'order', 'order': order.to_dict(),
                                'queue_seq': self._queue_positions.get(order.id),
                                'stack_seq': self._stack_positions.get(order.id)})
        if product is not None:
            self._append_event({'action': 'product', 'product': product.to_dict()})

    # ----- Validación -----
    @staticmethod
    def _clean_text(value: Any, field: str, max_len: int) -> str:
        if not isinstance(value, str):
            raise ValidationError(f'{field} debe ser texto.')
        cleaned = ' '.join(value.strip().split())
        if not cleaned:
            raise ValidationError(f'{field} no puede estar vacío.')
        if len(cleaned) > max_len or any(ord(ch) < 32 for ch in cleaned):
            raise ValidationError(f'{field} excede el largo permitido o tiene controles.')
        return cleaned

    @staticmethod
    def _parse_int(value: Any, field: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool):
            raise ValidationError(f'{field} debe ser entero.')
        try:
            number = int(value)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValidationError(f'{field} debe ser entero.') from exc
        if isinstance(value, float) or isinstance(value, str) and value.strip() not in (str(number), f'+{number}'):
            raise ValidationError(f'{field} debe ser entero sin decimales.')
        if not minimum <= number <= maximum:
            raise ValidationError(f'{field} debe estar entre {minimum} y {maximum}.')
        return number

    # ----- Menú -----
    def list_products(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self.products if include_inactive or p.active]

    def add_product(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            name = self._clean_text(payload.get('name'), 'Nombre', self.MAX_NAME)
            price = self._parse_int(payload.get('price_cop'), 'Precio', 1, self.MAX_PRODUCT_PRICE)
            if any(p.active and p.name.casefold() == name.casefold() for p in self.products):
                raise ConflictError('Ya existe un producto activo con ese nombre.')
            product = Product(id=str(uuid.uuid4()), name=name, price_cop=price)
            self.products.append(product)
            self._product_index[product.id] = product
            self._persist(product=product)
            return product.to_dict()

    def update_product(self, product_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            p = self._product_index.get(product_id)
            if p is None:
                raise NotFoundError('Producto no encontrado.')
            name = self._clean_text(payload.get('name', p.name), 'Nombre', self.MAX_NAME)
            price = self._parse_int(payload.get('price_cop', p.price_cop), 'Precio', 1, self.MAX_PRODUCT_PRICE)
            active = payload.get('active', p.active)
            if not isinstance(active, bool):
                raise ValidationError('active debe ser booleano.')
            if any(x.id != p.id and x.active and x.name.casefold() == name.casefold() for x in self.products):
                raise ConflictError('Ya existe otro producto activo con ese nombre.')
            p.name, p.price_cop, p.active = name, price, active
            self._persist(product=p)
            return p.to_dict()

    def deactivate_product(self, product_id: str) -> dict[str, Any]:
        with self._lock:
            p = self._product_index.get(product_id)
            if p is None:
                raise NotFoundError('Producto no encontrado.')
            p.active = False
            self._persist(product=p)
            return p.to_dict()

    # ----- Dos arreglos independientes: normal y alta -----
    def _enqueue(self, order: Order) -> None:
        self._queue_counter += 1
        self._queue_positions[order.id] = self._queue_counter
        (self.high_queue if order.priority else self.normal_queue).push(order)

    def create_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            customer = self._clean_text(payload.get('customer'), 'Cliente', self.MAX_CUSTOMER)
            priority = self._parse_int(payload.get('priority', 0), 'Prioridad', 0, 1)
            raw_items = payload.get('items')
            if not isinstance(raw_items, list) or not raw_items:
                raise ValidationError('Seleccione al menos un producto.')
            if len(raw_items) > self.MAX_DISTINCT_ITEMS:
                raise ValidationError(f'Máximo {self.MAX_DISTINCT_ITEMS} líneas de producto.')
            merged: dict[str, int] = {}
            for raw in raw_items:
                if not isinstance(raw, dict):
                    raise ValidationError('Producto del pedido inválido.')
                pid = raw.get('product_id')
                if not isinstance(pid, str):
                    raise ValidationError('Identificador de producto inválido.')
                qty = self._parse_int(raw.get('quantity'), 'Cantidad', 1, self.MAX_UNITS_PER_LINE)
                merged[pid] = merged.get(pid, 0) + qty
            if sum(merged.values()) > self.MAX_TOTAL_UNITS:
                raise ValidationError(f'Máximo {self.MAX_TOTAL_UNITS} unidades por pedido.')
            items = []
            for pid, qty in merged.items():
                if qty > self.MAX_UNITS_PER_LINE:
                    raise ValidationError(f'Máximo {self.MAX_UNITS_PER_LINE} unidades por producto.')
                p = self._product_index.get(pid)
                if p is None or not p.active:
                    raise ValidationError('Uno de los productos no existe o está inactivo.')
                items.append(OrderItem(product_id=p.id, name=p.name, unit_price_cop=p.price_cop, quantity=qty))
            order = Order(id=str(uuid.uuid4()), number=self.next_order_number,
                          customer=customer, priority=priority, items=items)
            self.next_order_number += 1
            self.orders[order.id] = order
            self._enqueue(order)
            self._counts['high' if priority else 'normal'] += 1
            self._persist(order=order)
            return order.to_dict()

    def process_next_order(self) -> dict[str, Any]:
        """Alta primero, hasta 3 consecutivos si hay pedidos normales; O(1) amortizado."""
        with self._lock:
            high = self._counts['high'] > 0
            normal = self._counts['normal'] > 0
            if not high and not normal:
                raise NotFoundError('No hay pedidos pendientes para preparar.')
            choose_high = high and (not normal or self._consecutive_priority < self.MAX_CONSECUTIVE_PRIORITY)
            queue = self.high_queue if choose_high else self.normal_queue
            order = queue.pop()
            if order is None:
                raise RuntimeError('Inconsistencia entre contadores y colas; reinicie el servidor.')
            label = 'high' if choose_high else 'normal'
            self._counts[label] -= 1
            self._counts['prepared'] += 1
            self._consecutive_priority = self._consecutive_priority + 1 if choose_high else 0
            order.status = 'prepared'
            order.prepared_at = utc_now_iso()
            self._queue_positions.pop(order.id, None)
            if self._counts[label] == 0:
                if choose_high:
                    self.high_queue = ArrayQueue()
                else:
                    self.normal_queue = ArrayQueue()
            self.prepared_stack.append(order.id)  # push LIFO O(1)
            self._stack_counter += 1
            self._stack_positions[order.id] = self._stack_counter
            self._persist(order=order)
            return order.to_dict()

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Marca como cancelado sin buscar ni desplazar elementos del arreglo."""
        with self._lock:
            order = self.orders.get(order_id)
            if order is None:
                raise NotFoundError('Pedido no encontrado.')
            if order.status != 'pending':
                raise ConflictError('Solo se pueden cancelar pedidos pendientes.')
            label = 'high' if order.priority else 'normal'
            self._counts[label] -= 1
            self._counts['cancelled'] += 1
            order.status = 'cancelled'
            self._queue_positions.pop(order.id, None)
            if self._counts[label] == 0:
                # Todos los restantes eran cancelados; libera el buffer completo.
                if label == 'high':
                    self.high_queue = ArrayQueue()
                else:
                    self.normal_queue = ArrayQueue()
            self._persist(order=order)
            return order.to_dict()

    # ----- Historial: pila LIFO, solo se borra el último preparado -----
    def delete_last_history_order(self) -> dict[str, Any]:
        """Extrae solo la cima de la pila de preparados; O(1) amortizado."""
        with self._lock:
            # Compatibilidad con historiales antiguos que tenían borrados arbitrarios.
            while self.prepared_stack and (self.prepared_stack[-1] not in self.orders or
                    self.orders[self.prepared_stack[-1]].status != 'prepared'):
                self.prepared_stack.pop()
            if not self.prepared_stack:
                raise NotFoundError('No hay pedidos preparados para borrar.')
            order_id = self.prepared_stack[-1]
            order = self.orders[order_id]
            self._append_event({'action': 'delete', 'id': order_id})
            self.prepared_stack.pop()
            del self.orders[order_id]
            self._queue_positions.pop(order_id, None)
            self._stack_positions.pop(order_id, None)
            self._counts['prepared'] -= 1
            return order.to_dict()

    def list_pending_orders(self, limit: int = 60) -> list[dict[str, Any]]:
        """Lee hasta k pendientes por arreglo, sin ordenar ni recorrer todo el historial."""
        with self._lock:
            limit = self._parse_int(limit, 'Límite', 1, 200)
            def active(queue: ArrayQueue):
                count = 0
                for order in queue.items[queue.head:]:
                    if order.status == 'pending':
                        yield order
                        count += 1
                        if count >= limit:
                            break
            highs = iter(active(self.high_queue))
            normals = iter(active(self.normal_queue))
            high = next(highs, None)
            normal = next(normals, None)
            streak = self._consecutive_priority
            result = []
            while len(result) < limit and (high is not None or normal is not None):
                if high is not None and (normal is None or streak < self.MAX_CONSECUTIVE_PRIORITY):
                    result.append(high.to_dict()); high = next(highs, None); streak += 1
                else:
                    result.append(normal.to_dict()); normal = next(normals, None); streak = 0
            return result

    def list_history(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            limit = self._parse_int(limit, 'Límite', 1, 200)
            offset = self._parse_int(offset, 'Desplazamiento', 0, 10_000_000)
            result = []
            skipped = 0
            for oid in reversed(self.prepared_stack):
                order = self.orders.get(oid)
                if order is None or order.status != 'prepared':
                    continue
                if skipped < offset:
                    skipped += 1
                    continue
                result.append(order.to_dict())
                if len(result) >= limit:
                    break
            return result

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                'products_active': sum(p.active for p in self.products),
                'orders_pending': self._counts['normal'] + self._counts['high'],
                'orders_prepared': self._counts['prepared'],
                'orders_cancelled': self._counts['cancelled'],
                'normal_queue_size': self._counts['normal'],
                'priority_queue_size': self._counts['high'],
                'stack_size': self._counts['prepared'],
            }
