# Estructuras de datos empleadas — FoodQueue v3.0

## 1. Arreglo dinámico: `products: list[Product]`

**Por qué:** un menú cambia de tamaño y requiere conservar el orden de exhibición. Python `list` administra automáticamente su capacidad.

**Cómo:** los productos se incorporan con `append`, se recorren para renderizar el menú y se recuperan por un diccionario auxiliar `product_id → objeto Product`. Los nombres duplicados se comprueban recorriendo los `m` productos existentes.

**Costos:** agregar al final `O(1)` amortizado; recorrer/buscar nombre `O(m)`; memoria `O(m)`.

## 2. Cola FIFO normal: arreglo e índice frontal

**Por qué:** los pedidos normales se sirven conforme a su orden de llegada.

**Cómo:** `normal_queue` es una instancia de `ArrayQueue`, que conserva referencias directas a objetos `Order` en un `list[Order]` y mantiene `head`, posición del próximo registro.

```python
self.items.append(order)              # insertar al final
order = self.items[self.head]         # consultar el frente
self.head += 1                          # extraer sin desplazar elementos
```

Evitar `pop(0)` es importante: desplaza todos los elementos restantes (O(n)). La cola compacta periódicamente los índices ya consumidos, repartiendo su costo sobre muchas extracciones (`O(1)` amortizado).

## 3. Cola con prioridad usando arreglos

**Por qué:** únicamente se distinguen dos niveles de servicio, por lo cual un heap genérico `heapq` añade complejidad innecesaria. Separar pedidos por tipo desde la inserción elimina búsquedas de prioridad durante la preparación.

**Cómo:** `high_queue` y `normal_queue` son arreglos independientes con índices de cabeza. Cada objeto de pedido entra **directamente en uno** según su atributo `priority`:

- `0` → arreglo normal.
- `1` → arreglo de prioridad alta.

`process_next_order()` consulta dos contadores enteros (`_counts['high']`, `_counts['normal']`) y decide en tiempo constante qué arreglo desencolar. Dentro de cada arreglo se respeta FIFO.

**Regla anti-inanición:** cuando existen pedidos normales esperando, después de atender tres pedidos de prioridad alta seguidos se atiende uno normal. Si no hay normales, se siguen atendiendo altos. Es una política de turnos, no una búsqueda ordenada de prioridades.

**Cancelación:** el estado de un pedido cambia a `cancelled` en el diccionario y en SQLite; no se busca el ID dentro del arreglo. Cuando el cursor alcanza una entrada cancelada la salta. Cada entrada se descarta una sola vez, por lo que el costo amortizado de consumir las cancelaciones sigue siendo constante, aunque una operación puntual podría saltar varias seguidas.

**Costos:** inserción O(1) amortizado; extraer siguiente O(1) amortizado; decisión de prioridad O(1); conteos O(1). Dos arreglos de referencias + diccionario requieren memoria proporcional a la cantidad de pedidos activos/históricos cargados.

## 4. Pila LIFO: `prepared_stack: list[str]`

**Por qué:** guardar los IDs en el orden de preparación facilita demostrar el orden LIFO y presentar los más recientes en primer lugar.

**Cómo:** al preparar, `prepared_stack.append(order.id)` (push). La lectura visual obtiene registros de SQLite ordenando `stack_seq` descendente. No existe operación de «deshacer». Borrar un registro individual elimina su fila SQLite y su objeto indexado; la entrada residual en el arreglo se descarta durante una compactación eventual. Esta técnica evita hacer `list.remove(id)`, cuyo coste sería O(h) cada vez.

**Costos:** push O(1), borrado por ID O(1) amortizado en memoria + escritura SQLite, borrado total O(h). La pila sigue representando el orden temporal, aunque el borrado arbitrario no es una operación LIFO estricta; esta distinción debe explicarse en la sustentación.

## 5. Estructuras auxiliares e índices

- `orders: dict[str, Order]`: acceso medio O(1) al pedido por UUID.
- `_counts`: contadores incrementales por estado/prioridad, para no calcular estadísticas mediante recorridos.
- `_queue_positions`: secuencia de inserción para restaurar las colas después de reiniciar.
- `_stack_positions`: secuencia de preparación para reconstruir el historial.
- SQLite con índices `(status, priority, queue_seq, number)` y `(status, stack_seq DESC)` para consultas limitadas.

**SQLite no sustituye las estructuras académicas**: conserva datos entre ejecuciones. Los dos arreglos implementan las colas, el menú usa un arreglo dinámico y el historial conserva una pila.

## Ejemplo de planificación

Llegan `N1, A1, A2, A3, A4, N2` (`N` normal, `A` alta). Dos arreglos:

```text
high_queue   = [A1, A2, A3, A4]   head = 0
normal_queue = [N1, N2]           head = 0

Atención: A1 → A2 → A3 → N1 → A4 → N2
```

En cada paso solo se consulta el frente del arreglo escogido, sin recorrer los otros pedidos.
