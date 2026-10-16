# Documento explicativo: estructuras de datos en FoodQueue

## 1. Arreglo dinámico — menú de productos

**Implementación:** `list[Product]` (`self.products`).

**Por qué:** el menú necesita una colección que crezca o disminuya sin conocer un tamaño máximo desde el inicio. Además, el orden de inserción es útil para presentar el catálogo al usuario.

**Cómo:** al crear un producto se usa `append()`, con costo amortizado O(1). Para mostrar el menú se recorre el arreglo, O(n). Se mantiene adicionalmente un diccionario `id -> Product` para que localizar un producto al construir pedidos sea O(1) promedio.

**Decisión de borrado:** se usa borrado lógico (`active=False`) en lugar de quitar físicamente productos, porque un pedido histórico debe seguir mostrando lo que se vendió aunque el producto deje de ofrecerse.

## 2. Cola FIFO — pedidos normales

**Implementación:** `collections.deque[str]` (`self.normal_queue`).

**Por qué:** un restaurante normalmente procesa pedidos por orden de llegada. Una cola modela directamente FIFO: First In, First Out.

**Cómo:** `append(id)` agrega al final O(1) y `popleft()` retira el primero O(1). Se evita usar `list.pop(0)`, porque desplazaría todos los elementos y costaría O(n).

## 3. Cola con prioridad — pedidos altos y urgentes

**Implementación:** `heapq`, un min-heap, almacenado en `self.priority_queue`.

**Por qué:** ciertos pedidos pueden requerir atención antes que los normales. Un heap evita reordenar toda la colección cada vez que llega un pedido nuevo.

**Cómo:** cada entrada tiene `(-prioridad, numero_pedido, id)`. El signo negativo convierte la mayor prioridad lógica en el menor valor del min-heap. El número de pedido resuelve empates manteniendo el orden de llegada. `heappush()` y `heappop()` cuestan O(log n).

**Equidad:** para evitar que una llegada continua de pedidos urgentes deje esperando indefinidamente a los normales, solo se procesan hasta 3 prioritarios consecutivos si hay normales esperando.

## 4. Pila LIFO — historial de preparados

**Implementación:** `list[str]` (`self.prepared_stack`).

**Por qué:** la acción natural de “deshacer” debe afectar al último pedido preparado. Esto corresponde a LIFO: Last In, First Out.

**Cómo:** al preparar un pedido se hace `append(id)` O(1); al deshacer, `pop()` O(1). El pedido vuelve a la cola normal o de prioridad según corresponda.

## 5. Estructuras auxiliares

`dict` se usa únicamente como índice para ubicar productos y pedidos por ID en O(1) promedio. Su existencia mejora el rendimiento y no reemplaza la función semántica de las cuatro estructuras lineales exigidas.

## 6. Complejidad resumida

| Operación | Estructura | Complejidad esperada |
|---|---|---:|
| Agregar producto | list | O(1) amortizado |
| Buscar producto por ID | dict auxiliar | O(1) promedio |
| Encolar normal | deque | O(1) |
| Desencolar normal | deque | O(1) |
| Encolar prioritario | heapq | O(log n) |
| Extraer prioritario | heapq | O(log n) |
| Push historial | list/pila | O(1) amortizado |
| Pop historial | list/pila | O(1) |
| Persistir estado JSON | archivo completo | O(P + O) |

P = número de productos; O = número total de pedidos persistidos.
