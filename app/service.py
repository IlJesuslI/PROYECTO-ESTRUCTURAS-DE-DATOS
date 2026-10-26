"""FoodQueue: catálogo dinámico, dos colas sobre arreglos y pila histórica.

Encolado / extracción: O(1) amortizado, sin recorrer toda la cola.
Persistencia incremental: SQLite; lectura de historial paginada e indexada.
"""
from __future__ import annotations

import json
import sqlite3
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
        self.db_path = self.state_path.with_suffix('.sqlite3')
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
            high_ids = sorted(set(old_priority_ids), key=lambda oid: self.orders[oid].number)
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
        is_new = not self.db_path.exists()
        self._db = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        self._db.execute('PRAGMA journal_mode=WAL')
        self._db.execute('PRAGMA busy_timeout=30000')
        self._db.executescript('''
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY, payload TEXT NOT NULL, position INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY, number INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL, priority INTEGER NOT NULL,
                queue_seq INTEGER, stack_seq INTEGER, payload TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_orders_pending
                ON orders(status, priority, queue_seq, number);
            CREATE INDEX IF NOT EXISTS idx_orders_prepared
                ON orders(status, stack_seq DESC);
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY, value INTEGER NOT NULL
            );
        ''')
        if is_new:
            if self.state_path.exists():
                self._load_legacy_json()
            else:
                self._seed_demo_menu()
            self._persist_all()
            return

        # Una sola migración: prioridad 2 (urgente) pasa a 1 (alta), también en el JSON.
        meta = dict(self._db.execute('SELECT key, value FROM metadata'))
        if meta.get('schema_version', 2) < 3:
            with self._db:
                for oid, raw in self._db.execute('SELECT id,payload FROM orders WHERE priority > 1').fetchall():
                    obj = json.loads(raw)
                    obj['priority'] = 1
                    self._db.execute('UPDATE orders SET priority=1,payload=? WHERE id=?',
                                     (json.dumps(obj, ensure_ascii=False, separators=(',', ':')), oid))
                # En v2 los pedidos altos de heapq no tenían queue_seq.
                # Asignar una secuencia a los históricos ANTES de registrar nuevos,
                # para no cambiar su orden tras el siguiente reinicio.
                next_seq = max(int(meta.get('queue_counter', 0)),
                               int(self._db.execute('SELECT COALESCE(MAX(queue_seq),0) FROM orders').fetchone()[0]))
                for (oid,) in self._db.execute("""SELECT id FROM orders
                        WHERE status='pending' AND queue_seq IS NULL
                        ORDER BY number""").fetchall():
                    next_seq += 1
                    self._db.execute('UPDATE orders SET queue_seq=? WHERE id=?', (next_seq, oid))
                self._db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('queue_counter', next_seq))
                self._db.execute('INSERT OR REPLACE INTO metadata VALUES (?,?)', ('schema_version', 3))
            meta['schema_version'] = 3
            meta['queue_counter'] = next_seq

        self.products = [Product(**json.loads(p)) for (p,) in
                         self._db.execute('SELECT payload FROM products ORDER BY position')]
        self._rebuild_product_index()
        normal_entries: list[tuple[int, int, str]] = []
        high_entries: list[tuple[int, int, str]] = []
        stack_entries: list[tuple[int, int, str]] = []
        for oid, status, priority, queue_seq, stack_seq, raw in self._db.execute(
                'SELECT id,status,priority,queue_seq,stack_seq,payload FROM orders'):
            o = Order.from_dict(json.loads(raw))
            o.priority = 1 if o.priority > 0 else 0
            self.orders[oid] = o
            if status == 'pending':
                entry = (queue_seq if queue_seq is not None else o.number, o.number, oid)
                (high_entries if o.priority else normal_entries).append(entry)
            elif status == 'prepared':
                stack_entries.append((stack_seq if stack_seq is not None else o.number, o.number, oid))
            if queue_seq is not None:
                self._queue_positions[oid] = queue_seq
            if stack_seq is not None:
                self._stack_positions[oid] = stack_seq
        self.normal_queue = ArrayQueue(self.orders[oid] for _, _, oid in sorted(normal_entries))
        self.high_queue = ArrayQueue(self.orders[oid] for _, _, oid in sorted(high_entries))
        self.prepared_stack = [oid for _, _, oid in sorted(stack_entries)]
        self.next_order_number = max(meta.get('next_order_number', 1),
                                     max((o.number for o in self.orders.values()), default=0) + 1)
        self._consecutive_priority = meta.get('consecutive_priority', 0)
        self._queue_counter = max(meta.get('queue_counter', 0),
                                  max(self._queue_positions.values(), default=0))
        self._stack_counter = max(meta.get('stack_counter', 0),
                                  max(self._stack_positions.values(), default=0))
        self._calculate_counts()

    def _calculate_counts(self) -> None:
        self._counts = {'normal': 0, 'high': 0, 'prepared': 0, 'cancelled': 0}
        for o in self.orders.values():
            if o.status == 'pending':
                self._counts['high' if o.priority else 'normal'] += 1
            elif o.status in self._counts:
                self._counts[o.status] += 1

    def _write_order(self, order: Order) -> None:
        self._db.execute('''INSERT OR REPLACE INTO orders
            (id, number, status, priority, queue_seq, stack_seq, payload)
            VALUES (?,?,?,?,?,?,?)''',
            (order.id, order.number, order.status, order.priority,
             self._queue_positions.get(order.id), self._stack_positions.get(order.id),
             json.dumps(order.to_dict(), ensure_ascii=False, separators=(',', ':'))))

    def _write_meta(self) -> None:
        self._db.executemany('INSERT OR REPLACE INTO metadata VALUES (?,?)', (
            ('schema_version', 3), ('next_order_number', self.next_order_number),
            ('consecutive_priority', self._consecutive_priority),
            ('queue_counter', self._queue_counter), ('stack_counter', self._stack_counter)
        ))

    def _persist_all(self) -> None:
        with self._db:
            for position, p in enumerate(self.products):
                self._db.execute('INSERT OR REPLACE INTO products VALUES (?,?,?)',
                                 (p.id, json.dumps(p.to_dict(), ensure_ascii=False), position))
            for o in self.orders.values():
                self._write_order(o)
            self._write_meta()

    def _persist(self, *, order: Order | None = None, product: Product | None = None) -> None:
        with self._db:
            if order is not None:
                self._write_order(order)
            if product is not None:
                # Solo catálogo: búsqueda de posición O(m), no depende de n pedidos.
                position = next(i for i, p in enumerate(self.products) if p.id == product.id)
                self._db.execute('INSERT OR REPLACE INTO products VALUES (?,?,?)',
                                 (product.id, json.dumps(product.to_dict(), ensure_ascii=False), position))
            self._write_meta()

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

    # ----- Historial: solo BORRAR, sin deshacer -----
    def delete_history_order(self, order_id: str) -> dict[str, Any]:
        """Elimina definitivamente un pedido preparado (memoria y SQLite)."""
        with self._lock:
            order = self.orders.get(order_id)
            if order is None:
                raise NotFoundError('Pedido no encontrado.')
            if order.status != 'prepared':
                raise ConflictError('Solo pueden borrarse pedidos preparados del historial.')
            with self._db:
                self._db.execute('DELETE FROM orders WHERE id=? AND status=?', (order_id, 'prepared'))
            del self.orders[order_id]
            self._queue_positions.pop(order_id, None)
            self._stack_positions.pop(order_id, None)
            self._counts['prepared'] -= 1
            # La pila conserva una referencia obsoleta (tombstone), para no recorrerla.
            # Se compacta ocasionalmente, amortizando el coste.
            if len(self.prepared_stack) > 256 and len(self.prepared_stack) > self._counts['prepared'] * 2:
                self.prepared_stack = [oid for oid in self.prepared_stack if oid in self.orders
                                       and self.orders[oid].status == 'prepared']
            return order.to_dict()

    def clear_history(self) -> int:
        """Borrado masivo explícito, O(h). No afecta pedidos pendientes o cancelados."""
        with self._lock:
            to_delete = [oid for oid in self.prepared_stack if oid in self.orders
                         and self.orders[oid].status == 'prepared']
            with self._db:
                self._db.execute("DELETE FROM orders WHERE status='prepared'")
            for oid in to_delete:
                self.orders.pop(oid, None)
                self._queue_positions.pop(oid, None)
                self._stack_positions.pop(oid, None)
            deleted = self._counts['prepared']
            self._counts['prepared'] = 0
            self.prepared_stack.clear()
            return deleted

    def list_pending_orders(self, limit: int = 60) -> list[dict[str, Any]]:
        """Solo primeras k entradas de cada prioridad usando índice SQL; no ordena n pedidos."""
        with self._lock:
            limit = self._parse_int(limit, 'Límite', 1, 200)
            def read(priority: int) -> list[dict[str, Any]]:
                rows = self._db.execute('''SELECT payload FROM orders
                    WHERE status='pending' AND priority=?
                    ORDER BY queue_seq, number LIMIT ?''', (priority, limit))
                return [json.loads(raw) for (raw,) in rows]
            highs, normals = read(1), read(0)
            hi = no = 0
            streak = self._consecutive_priority
            result: list[dict[str, Any]] = []
            while len(result) < limit and (hi < len(highs) or no < len(normals)):
                if hi < len(highs) and (no >= len(normals) or streak < self.MAX_CONSECUTIVE_PRIORITY):
                    result.append(highs[hi]); hi += 1; streak += 1
                elif no < len(normals):
                    result.append(normals[no]); no += 1; streak = 0
                else:
                    break
            return result

    def list_history(self, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._lock:
            limit = self._parse_int(limit, 'Límite', 1, 200)
            offset = self._parse_int(offset, 'Desplazamiento', 0, 10_000_000)
            rows = self._db.execute('''SELECT payload FROM orders WHERE status='prepared'
                ORDER BY stack_seq DESC LIMIT ? OFFSET ?''', (limit, offset))
            return [json.loads(raw) for (raw,) in rows]

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
