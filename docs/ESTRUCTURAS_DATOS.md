# Estructuras de datos en FoodQueue v4.1: por qué y cómo se utilizan

## 1. Objetivo de diseño
FoodQueue demuestra el uso de **arreglos dinámicos, colas FIFO, colas con prioridad y pilas LIFO** en un sistema de pedidos. Las estructuras lineales realizan el almacenamiento y el ordenamiento operativo; los diccionarios auxiliares aceleran las búsquedas por identificador. La persistencia JSON/JSONL guarda los cambios entre ejecuciones y **no sustituye** a las estructuras en memoria.

El núcleo se encuentra en `app/service.py`, especialmente en `ArrayQueue` y `FoodQueueService`.

## 2. Arreglo dinámico: catálogo de productos
**Dónde:** `self.products: list[Product] = []`.

**Por qué:** el menú puede crecer durante la ejecución sin definir un tamaño fijo. La lista conserva el orden de los productos y facilita recorrerlos para mostrarlos.

**Cómo:**
- **Agregar:** se crea un `Product` y se inserta al final mediante `self.products.append(product)`. La inserción es **O(1) amortizado**; la función completa `add_product()` es **O(m)** porque antes recorre el menú para evitar nombres activos repetidos.
- **Editar:** `update_product()` localiza el objeto por ID en `_product_index`, valida los nuevos datos y modifica sus atributos. La búsqueda por ID es **O(1) promedio**, pero la validación de nombres hace que la operación completa sea **O(m)**.
- **Desactivar:** `deactivate_product()` busca por ID y establece `active = False`. No elimina físicamente el objeto ni desplaza elementos: **O(1) promedio en memoria**.
- **Reactivar:** `update_product()` puede establecer `active = True`; como valida nombres, su costo completo es **O(m)**.
- **Listar:** `list_products()` recorre los productos y filtra los activos; **O(m)** tiempo y hasta **O(m)** espacio de salida.

Aquí `m` es el número de productos. Acceder a `self.products[i]` es O(1), pero no se debe confundir el **índice del arreglo** con el **ID único** de un producto.

### Índice auxiliar por ID
**Dónde:** `self._product_index: dict[str, Product]`.

**Por qué:** recorrer el menú para encontrar cada ID sería O(m). El diccionario permite recuperar una referencia al objeto con `get(product_id)` en **O(1) promedio**. La lista y el diccionario apuntan al mismo producto, por lo que cambiar el objeto no exige reemplazarlo en el arreglo.

## 3. Cola FIFO mediante arreglo dinámico
**Dónde:** clase `ArrayQueue`, con `items: list[Order]` y `head: int`.

**Por qué:** dentro de una misma prioridad, los pedidos deben atenderse en el orden de llegada (**First In, First Out**). Una lista con `pop(0)` desplazaría elementos y costaría O(n) por extracción.

**Cómo:**
- **Encolar:** `push(order)` ejecuta `items.append(order)`; **O(1) amortizado**.
- **Desencolar:** `pop()` lee `items[head]` y aumenta `head`; evita desplazar el resto. La extracción de un pedido vigente es **O(1) amortizado**.
- **Cancelaciones:** el pedido se marca `cancelled` en el índice `orders`; cuando la cola llega a él, lo salta. Por ello, una extracción concreta puede recorrer varias entradas canceladas.
- **Compactación:** `_compact()` elimina de una vez el prefijo ya consumido cuando alcanza al menos la mitad del arreglo. Esa operación puntual es O(n), pero su costo se amortiza entre las extracciones anteriores.

Ejemplo: `items = [A, B, C]`, `head = 0`. Tras preparar A, `head = 1`; B y C conservan sus posiciones hasta una compactación posterior.

## 4. Cola con prioridad mediante dos arreglos
**Dónde:** `self.high_queue = ArrayQueue()` y `self.normal_queue = ArrayQueue()`.

**Por qué:** separar los pedidos en dos colas permite escoger la prioridad sin buscar el pedido más importante dentro de un único arreglo. El proyecto utiliza **Normal (0)** y **Alta (1)**, sin `heapq`.

**Cómo:**
1. `create_order()` valida el pedido y lo agrega a la cola correspondiente mediante `_enqueue()`.
2. `process_next_order()` consulta los contadores de pedidos pendientes.
3. Se elige Alta cuando hay pedidos Altos, salvo que ya se hayan atendido tres Altos consecutivos y exista algún Normal esperando.
4. Si corresponde Normal, se atiende el primero de su cola y se reinicia el contador de Altos consecutivos.
5. Dentro de cada cola se mantiene el orden FIFO.

**Ejemplo, con ambas colas no vacías:** Alta 1 → Alta 2 → Alta 3 → Normal 1 → Alta 4.

**Complejidad:** elegir qué cola atender es **O(1)**; encolar es **O(1) amortizado**; extraer es **O(1) amortizado**, con costo adicional puntual si hay entradas canceladas que saltar. **Mostrar k pedidos** requiere construir la salida y no es O(1): su costo depende de los elementos visitados y de los cancelados omitidos.

## 5. Pila LIFO: historial de preparados
**Dónde:** `self.prepared_stack: list[str] = []`.

**Por qué:** la operación de borrado del historial debe afectar únicamente al último pedido preparado (**Last In, First Out**). La pila modela exactamente esa restricción.

**Cómo:**
- **Apilar:** cuando un pedido se prepara, `process_next_order()` ejecuta `prepared_stack.append(order.id)`; **O(1) amortizado**.
- **Consultar:** `list_history()` recorre la pila en sentido inverso, del más reciente al más antiguo; la lectura depende del número de registros recorridos.
- **Borrar último:** `delete_last_history_order()` toma el ID de la cima y utiliza `prepared_stack.pop()`. También actualiza el índice `orders`, los contadores y el diario JSONL.
- **Restricción:** no se ofrece borrar un pedido intermedio ni borrar todo el historial.

**Complejidad:** agregar o retirar la cima de una pila implementada con lista es **O(1) amortizado**. El método de borrado puede retirar antes entradas antiguas inválidas heredadas de versiones anteriores; ese saneamiento puede costar más en una llamada particular.

## 6. Diccionario auxiliar de pedidos y cancelación
**Dónde:** `self.orders: dict[str, Order]`.

**Por qué:** cancelar un pedido por ID recorriendo todas las colas sería costoso. El diccionario localiza directamente el objeto, que también está referenciado desde la cola correspondiente.

**Cómo:** `cancel_order()` consulta `orders.get(order_id)`, verifica que el pedido esté pendiente y cambia su estado a `cancelled`. No lo elimina de la mitad del arreglo; la cola lo descartará cuando llegue a su posición.

**Complejidad:** **O(1) promedio en memoria** para localizar y marcar el pedido; el costo de descartar físicamente entradas canceladas se difiere a extracciones posteriores.

## 7. Resumen de complejidades
| Operación | Estructura principal | Complejidad en memoria |
|---|---|---|
| Insertar al final del catálogo | Arreglo dinámico | O(1) amortizado |
| Agregar producto con validación de nombre | Arreglo dinámico | O(m) |
| Editar producto con validación de nombre | Arreglo + diccionario | O(m) |
| Desactivar producto por ID | Diccionario auxiliar | O(1) promedio |
| Listar productos | Arreglo dinámico | O(m) |
| Encolar pedido | Arreglo con índice de cabeza | O(1) amortizado |
| Elegir Alta o Normal | Dos colas y contador | O(1) |
| Extraer siguiente pendiente | Cola FIFO | O(1) amortizado; puede saltar cancelados |
| Cancelar pedido por ID | Diccionario + marca | O(1) promedio |
| Apilar pedido preparado | Pila con lista | O(1) amortizado |
| Borrar último preparado | Pila con lista | O(1) amortizado en el caso habitual |
| Mostrar k pedidos | Recorrido de colas | Depende de k y de entradas omitidas |

**Precisiones:** O(1) en diccionarios significa **promedio/esperado**, no garantía absoluta en el peor caso. O(1) amortizado admite operaciones puntuales más costosas, como redimensionar o compactar una lista. Estas cifras describen las **estructuras en memoria**, no el tiempo total de una petición HTTP ni la escritura en disco.

## 8. Persistencia: JSON y JSONL
**Dónde:** `data/state.json` y `data/state.jsonl`.

**Por qué:** el proyecto necesita recuperar productos y pedidos tras reiniciar sin utilizar SQLite.

**Cómo:** `state.json` aporta el estado inicial cuando existe; `state.jsonl` registra eventos incrementales (altas, cambios de estado y eliminaciones). Al iniciar, el servicio reconstruye las estructuras en memoria a partir de estos archivos.

**Limitación:** el tiempo de arranque crece con el tamaño del diario. JSONL es un mecanismo de persistencia, **no una quinta estructura lineal** ni una base transaccional multiusuario.

## 9. Relación con los requisitos académicos
El proyecto utiliza y demuestra, con código real, al menos tres estructuras: **arreglo dinámico** (catálogo), **cola FIFO / cola con prioridad** (pedidos) y **pila LIFO** (historial). Los diccionarios son índices complementarios para acelerar búsquedas; no sustituyen el papel de las estructuras principales.

## 10. Archivos clave para revisar el funcionamiento
- `app/service.py`: estructuras, operaciones, prioridades y persistencia.
- `app/models.py`: modelos de productos y pedidos.
- `server.py`: rutas HTTP que conectan interfaz y servicio.
- `static/index.html` y `static/app.js`: controles y eventos de la interfaz.
- `tests/test_service.py`: pruebas de comportamiento.
