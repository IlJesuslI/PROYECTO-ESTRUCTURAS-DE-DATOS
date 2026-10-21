# Documento explicativo

## 1. Introducción

FoodQueue es una aplicación web local para administrar el menú de un restaurante y gestionar pedidos de acuerdo con su prioridad. La aplicación permite registrar productos, crear pedidos con diferentes cantidades, procesar pedidos, cancelar pedidos pendientes, consultar el historial y deshacer la última preparación.

La lógica principal se encuentra en `app/service.py`, mientras que `app/models.py` define los modelos `Product`, `OrderItem` y `Order`. La interfaz está desarrollada con HTML, CSS y JavaScript, y la comunicación con la lógica de Python se realiza mediante una API HTTP local.

El diseño de FoodQueue utiliza cuatro estructuras de datos principales:

1. Arreglo dinámico para administrar el catálogo de productos.
2. Cola FIFO para procesar pedidos normales.
3. Cola con prioridad implementada mediante un heap para atender pedidos prioritarios.
4. Pila LIFO para administrar el historial de pedidos preparados y permitir deshacer la última preparación.

También se emplean diccionarios como estructuras auxiliares de acceso rápido y archivos JSON para conservar la información entre ejecuciones.

## 2. Arreglo dinámico | Catálogo de productos

### 2.1. Implementación y propósito

El catálogo se almacena en el atributo `self.products`, definido como una lista de objetos `Product`:

```python
self.products: list[Product] = []
```

La lista permite almacenar una cantidad variable de productos sin tener que establecer previamente un tamaño máximo. Cada producto contiene un identificador, un nombre, un precio y un indicador que señala si continúa activo.

Cuando se agrega un producto, el programa crea el objeto correspondiente y lo incorpora mediante:

```python
self.products.append(product)
```

Esta operación tiene un costo amortizado de O(1). Esto significa que agregar un elemento normalmente es una operación constante, aunque algunas inserciones pueden requerir ampliar la capacidad interna de la lista y copiar referencias. Al considerar una secuencia larga de inserciones el costo promedio por inserción sigue siendo constante.

### 2.2. ¿Por qué utilizar una lista y no un arreglo de tamaño fijo?

Un arreglo de tamaño fijo requiere determinar su capacidad con anticipación. Si el restaurante comienza con pocos productos y posteriormente amplía el menú, podría quedarse sin espacio o reservar memoria innecesariamente. En cambio, la lista de Python se adapta automáticamente al crecimiento de la colección. Además permite recorrer los productos en el orden en que fueron incorporados, lo cual resulta conveniente para presentar el catálogo.

### 2.3. ¿Por qué no utilizar una lista enlazada?

Una lista enlazada permite insertar o eliminar nodos en O(1) cuando ya se dispone de la referencia al nodo y se conocen sus posiciones relevantes. Sin embargo, encontrar un producto por su posición o por una propiedad como el nombre requiere recorrer los nodos con un costo O(n).

Para FoodQueue el acceso secuencial al catálogo es una operación natural y las búsquedas frecuentes por identificador se resuelven con un diccionario auxiliar. Por eso una lista enlazada añadiría complejidad de implementación sin aportar una ventaja decisiva para las operaciones principales del menú.

La lista dinámica de Python, por su implementación optimizada y su facilidad de uso, constituye una alternativa adecuada.

### 2.4. Eliminación lógica de productos

FoodQueue no elimina físicamente un producto cuando deja de ofrecerse, en su lugar cambia su atributo `active` a `False`. Esta decisión es importante porque los pedidos anteriores conservan el nombre y el precio del producto que se vendió. Si el producto se eliminara físicamente podrían perderse referencias útiles para consultar el historial.

El borrado lógico permite diferenciar entre los productos disponibles para nuevos pedidos y aquellos que se mantienen únicamente por razones históricas. Sin embargo, debe considerarse que agregar productos tiene un costo amortizado O(1), mientras que comprobar si ya existe un producto activo con el mismo nombre requiere recorrer la lista, en el peor caso con un costo O(P), donde P representa la cantidad de productos.

Asimismo, listar o filtrar el catálogo tiene un costo O(P), porque es necesario examinar sus elementos.

## 3. Diccionarios auxiliares

### 3.1. Implementación

Además de la lista de productos, FoodQueue mantiene el diccionario:

```python
self._product_index: dict[str, Product] = {}
```

La clave es el identificador del producto y el valor es el objeto correspondiente. Para localizar un producto al crear un pedido se utiliza una operación como:

```python
product = self._product_index.get(product_id)
```

Esta búsqueda tiene un costo promedio O(1) suponiendo un comportamiento normal de la tabla hash. En situaciones desfavorables las búsquedas pueden alcanzar O(P).

El sistema también almacena los pedidos en un diccionario:

```python
self.orders: dict[str, Order] = {}
```

De esta manera las estructuras de procesamiento guardan los identificadores de los pedidos y el diccionario permite recuperar el objeto completo cuando se necesita consultar o modificar su estado.

### 3.2. ¿Por qué no almacenar todos los productos únicamente en un diccionario?

Un diccionario sería adecuado para buscar productos por identificador, pero no reemplaza automáticamente todas las funciones de la lista. La lista representa directamente un catálogo ordenado por incorporación, facilita el recorrido secuencial y cumple el papel de arreglo dinámico. El diccionario en cambio está orientado a localizar elementos a partir de claves.

Mantener ambas estructuras permite aprovechar las ventajas de cada una:

- La lista conserva el catálogo y permite recorrerlo.
- El diccionario evita recorrer toda la lista cuando se conoce el identificador.

La contrapartida es que ambas estructuras deben mantenerse sincronizadas. Por eso al agregar un producto, FoodQueue lo incorpora tanto a la lista como al índice.

## 4. Cola FIFO | Pedidos normales

### 4.1. Implementación y funcionamiento

Los pedidos normales se almacenan en:

```python
self.normal_queue: deque[str] = deque()
```

La estructura utilizada es `collections.deque`, una colección que permite insertar y retirar elementos eficientemente por ambos extremos. Una cola FIFO (*First In, First Out*) sigue la regla «primero en entrar, primero en salir». En un restaurante esto permite atender los pedidos normales respetando el orden de llegada.

FoodQueue utiliza dos operaciones principales:

```python
self.normal_queue.append(order.id)
```

Esta operación incorpora el identificador al final de la cola con costo O(1).

```python
order_id = self.normal_queue.popleft()
```

Esta operación retira el primer identificador con costo O(1).

Por lo tanto, insertar y retirar pedidos normales no requiere desplazar todos los elementos que permanecen en espera.

### 4.2. ¿Por qué utilizar `deque` y no una lista convencional?

Una lista de Python permite agregar elementos al final con costo amortizado O(1), pero retirar el primer elemento mediante `pop(0)` tiene costo O(n) porque los elementos restantes deben desplazarse para ocupar el espacio liberado. Si existen muchos pedidos pendientes, repetir esta operación genera trabajo innecesario.

Por ejemplo, si hay 1.000 pedidos normales en una lista, retirar el primero puede implicar desplazar aproximadamente 999 referencias. Con `deque` la extracción del primer elemento se realiza en O(1), sin desplazar los demás pedidos.

### 4.3. Cancelación de pedidos

Cuando se cancela un pedido pendiente, FoodQueue cambia su estado a `cancelled`, pero no busca y elimina inmediatamente su identificador dentro de la cola. Esta estrategia se conoce como **eliminación perezosa**, cuando el identificador llega al frente de la cola el programa comprueba el estado del pedido y descarta las entradas que ya no están pendientes.

La decisión evita buscar una posición arbitraria dentro de la cola y eliminarla, operación que podría costar O(n).

## 5. Cola con prioridad | Pedidos de prioridad alta y urgente

### 5.1. Necesidad de una estructura diferente

No todos los pedidos deben recibir exactamente el mismo tratamiento. FoodQueue permite registrar pedidos con prioridad normal, alta o urgente. Mientras que los pedidos normales se procesan siguiendo FIFO, los pedidos prioritarios deben organizarse de manera que los urgentes tengan preferencia sobre los de prioridad alta.

Para ello, el sistema utiliza el módulo `heapq` de Python y almacena las entradas en una lista que representa un **min-heap**:

```python
self.priority_queue: list[tuple[int, int, str]] = []
```

Cada entrada contiene tres elementos:

```python
(-order.priority, order.number, order.id)
```

El primero representa la prioridad con signo negativo; el segundo corresponde al número secuencial del pedido, y el tercero es su identificador único.

### 5.2. ¿Cómo funciona el heap?

Un heap es una estructura parcialmente ordenada. En un min-heap, el elemento menor se encuentra en la raíz, por lo que puede consultarse y extraerse sin ordenar completamente todos los elementos.

Como `heapq` organiza los elementos de menor a mayor, FoodQueue utiliza la prioridad negativa para invertir el orden lógico:

- Prioridad urgente, representada por 2: valor `-2`.
- Prioridad alta, representada por 1: valor `-1`.

Como `-2` es menor que `-1`, el pedido urgente queda por delante del pedido de prioridad alta.

El segundo elemento de la tupla, `order.number`, permite resolver empates cuando dos pedidos tienen la misma prioridad, el número de pedido menor tiene preferencia. De esta manera los pedidos de igual prioridad conservan el orden de llegada.

### 5.3. Complejidad de las operaciones

La inserción se realiza mediante:

```python
heapq.heappush(self.priority_queue, entry)
```

Su costo es O(log H), donde H es la cantidad de entradas en el heap.

La extracción del siguiente pedido prioritario se realiza mediante:

```python
heapq.heappop(self.priority_queue)
```

Su costo también es O(log H), debido a los ajustes que se realizan para mantener la propiedad del heap.

### 5.4. ¿Por qué no utilizar una lista sin ordenar?

Una lista sin ordenar permite insertar un pedido al final en O(1) amortizado, pero encontrar el pedido de mayor prioridad exige revisar todos los elementos con costo O(H).

### 5.5. ¿Por qué no mantener la lista siempre ordenada?

Otra alternativa sería insertar cada pedido en una lista ordenada por prioridad y número de llegada. Así, el siguiente pedido estaría en una posición conocida. Sin embargo, encontrar la posición de inserción puede requerir O(log H) con búsqueda binaria, pero insertar el elemento en una lista de Python puede requerir desplazar otros elementos, con costo O(H).

### 5.6. Equidad y prevención de inanición

Priorizar siempre los pedidos urgentes podría provocar que los pedidos normales esperaran indefinidamente si siguen llegando nuevos pedidos prioritarios. Este problema se conoce como **inanición**.

FoodQueue establece un límite de tres pedidos prioritarios consecutivos cuando existen pedidos normales pendientes. Después de atender hasta tres pedidos prioritarios el sistema da turno a un pedido normal antes de continuar con los prioritarios, siempre que haya pedidos normales esperando.

La política también tiene un costo computacional, comprobar si existen pedidos normales pendientes puede requerir recorrer la cola con costo O(Q), donde Q es la cantidad de entradas en ella.

## 6. Pila LIFO | Historial y acción de deshacer

### 6.1. Implementación

FoodQueue utiliza una lista de Python como pila para registrar los identificadores de los pedidos preparados:

```python
self.prepared_stack: list[str] = []
```

Cuando se prepara un pedido su identificador se agrega al final de la lista mediante `append()`. Cuando el usuario solicita deshacer la última preparación, se utiliza `pop()` para recuperar el elemento más reciente. Este comportamiento corresponde a LIFO (*Last In, First Out*), el último pedido preparado es el primero que se recupera al deshacer.

### 6.2. ¿Por qué utilizar una pila?

La acción de deshacer normalmente debe revertir la operación más reciente. Una pila modela directamente esta relación temporal porque solo permite retirar el elemento situado en el tope. Por ejemplo, si se preparan los pedidos A, B y C, el tope de la pila será C. Al deshacer, C se recupera primero, si se vuelve a deshacer, se recupera B.

Esta propiedad hace que la pila sea adecuada para la funcionalidad implementada en `undo_last_prepared()`.

### 6.3. Complejidad y recuperación del pedido

Agregar un elemento al final de la lista utilizado como operación de apilamiento (*push*), tiene costo amortizado O(1). Retirar el último elemento, mediante *pop*, tiene costo O(1).

Una vez recuperado el pedido, FoodQueue cambia su estado de `prepared` a `pending` y lo devuelve a la cola correspondiente según su prioridad. Por tanto, deshacer no significa eliminar el pedido del sistema, sino cambiar su estado y reinsertarlo en el mecanismo de atención.

## 7. Persistencia mediante JSON

### 7.1. Necesidad de conservar el estado

Las estructuras en memoria permiten procesar pedidos eficientemente mientras el programa está en ejecución, pero por sí solas no garantizan que los datos permanezcan después de cerrar el servidor.

FoodQueue conserva el estado en `data/state.json`. Al iniciar, el método `_load()` lee el archivo y reconstruye los productos, los pedidos y las estructuras de procesamiento. Después de las modificaciones relevantes, `_persist()` serializa el estado y lo guarda nuevamente.

El archivo conserva, entre otros datos, los productos, los pedidos, la cola normal, el heap prioritario y la pila del historial.

### 7.2. ¿Por qué utilizar JSON?

JSON es un formato de texto sencillo que permite representar objetos, listas, números, cadenas y valores booleanos. Es fácil de inspeccionar, no requiere instalar un gestor de bases de datos y resulta apropiado para una aplicación académica local.

### 7.3. Complejidad y limitaciones

Si P es la cantidad de productos y O la cantidad total de pedidos almacenados, serializar y escribir el estado completo tiene un costo aproximado O(P + O), además del costo de entrada/salida del archivo. Esto significa que guardar el estado puede ser mucho más costoso que insertar un elemento en una cola o una pila. Cada nueva modificación vuelve a procesar los registros almacenados incluso cuando solo ha cambiado un pedido.

Por ello, aunque `deque` y `heapq` mantienen operaciones eficientes, el guardado completo del JSON puede convertirse en el principal cuello de botella cuando aumenta el historial.

El programa utiliza un archivo temporal y luego `os.replace()` para reducir el riesgo de dejar el archivo principal parcialmente escrito durante una actualización. Esta estrategia mejora la seguridad de la escritura aunque no equivale a todas las garantías de durabilidad y transaccionalidad de una base de datos.

## 8. Conclusión

La selección de estructuras de datos en FoodQueue responde a las necesidades particulares de cada operación. La lista dinámica permite administrar un catálogo que puede crecer con el tiempo. El diccionario auxiliar facilita el acceso a productos y pedidos mediante identificadores. `deque` representa de forma eficiente la cola FIFO de pedidos normales, mientras que `heapq` permite seleccionar pedidos prioritarios sin ordenar toda la colección después de cada inserción. Por su parte, la pila LIFO hace posible recuperar el último pedido preparado y deshacer esa operación.

La implementación utiliza estructuras disponibles en la biblioteca estándar de Python en lugar de desarrollar desde cero las operaciones internas de listas, colas y heaps. Esto reduce la complejidad del código y permite aprovechar implementaciones optimizadas, manteniendo explícita la lógica del sistema.

Finalmente, el análisis muestra que una estructura eficiente no garantiza que todas las operaciones del programa tengan el mismo nivel de eficiencia. En FoodQueue, el guardado completo del estado en JSON puede dominar el tiempo de ejecución conforme crece el historial. 