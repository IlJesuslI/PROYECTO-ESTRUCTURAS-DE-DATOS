# Índice de funcionamiento — FoodQueue

1. **Inicio del sistema**
   1. Ejecutar `python server.py`.
   2. El servidor crea/carga `data/state.json`.
   3. Se reconstruyen el arreglo, las colas y la pila.
   4. Abrir `http://127.0.0.1:8000`.

2. **Gestión del menú — arreglo dinámico**
   1. Entrar a **Menú**.
   2. Registrar nombre y precio.
   3. El producto se agrega con `list.append()`.
   4. Los productos se muestran en el selector de pedidos.
   5. La eliminación es lógica (`active = False`) para no romper el historial.

3. **Creación del pedido**
   1. Entrar a **Pedidos**.
   2. Escribir cliente.
   3. Seleccionar prioridad: normal, alta o urgente.
   4. Indicar cantidades.
   5. El backend valida cantidades, existencia y precio.
   6. Se crea una copia del nombre/precio dentro del pedido para conservar el valor histórico.

4. **Encolado**
   1. Prioridad normal → `deque.append()`.
   2. Prioridad alta/urgente → `heapq.heappush()`.
   3. En prioridad igual, se conserva el orden de llegada usando el número secuencial del pedido.

5. **Preparar siguiente pedido**
   1. El sistema consulta primero la cola de prioridad.
   2. Puede atender hasta 3 prioritarios consecutivos.
   3. Si existe un pedido normal, el cuarto turno se reserva para la cola FIFO.
   4. El pedido procesado cambia a `prepared`.
   5. Su ID se inserta en la pila de preparados mediante `append()`.

6. **Historial y deshacer — pila**
   1. La pestaña **Historial** presenta primero el último preparado.
   2. **Deshacer último** ejecuta `pop()`.
   3. El pedido vuelve al estado pendiente.
   4. Se reencola según su prioridad original.

7. **Cancelación**
   1. Solo se cancelan pedidos pendientes.
   2. La orden pasa a estado `cancelled`.
   3. Si su ID quedó físicamente en una cola, se descarta de forma perezosa cuando llegue al frente; así se evita buscar/eliminar en O(n).

8. **Persistencia**
   1. Cada operación mutante escribe un archivo temporal.
   2. `os.replace()` reemplaza el estado de forma atómica.
   3. Al reiniciar, las colas y la pila se reconstruyen según el estado de los pedidos.

9. **Pruebas**
   1. Ejecutar `python run_tests.py`.
   2. Se comprueba FIFO, prioridad, equidad, LIFO, validaciones y reconstrucción tras reinicio.
