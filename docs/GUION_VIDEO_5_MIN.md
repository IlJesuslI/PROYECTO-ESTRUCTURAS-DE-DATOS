# Guion de presentación — duración objetivo 4:40

**0:00–0:30 | Presentación del problema (30 s)**

“Este es FoodQueue, un sistema de pedidos de restaurante desarrollado en Python y JavaScript. Ayuda a crear pedidos, organizar turnos y consultar registros preparados. El proyecto demuestra arreglos dinámicos, colas, colas con prioridad y pila.”

**0:30–1:35 | Estructuras y complejidad (65 s)**

Mostrar `app/service.py` y señalar:

- Menú con `list[Product]`.
- `high_queue` y `normal_queue` con dos arreglos `list` e índice `head`.
- Crear un pedido inserta directamente su ID en el arreglo correspondiente, O(1) amortizado.
- Preparar el siguiente consulta contadores y extrae `items[head]`, sin `pop(0)` ni búsqueda global: O(1) amortizado.
- `prepared_stack` conserva el orden de preparación, push O(1).

**1:35–2:40 | Demostración funcional (65 s)**

En el navegador, crear un pedido normal y tres de prioridad alta. Mostrar que primero se preparan los tres de alta y luego el normal. Explicar FIFO dentro de cada arreglo y regla de equidad. Mostrar el contador que se actualiza.

**2:40–3:25 | Historial y menú (45 s)**

Abrir Historial, enseñar el último preparado y usar **Borrar** en un registro. Aclarar que no existe **Deshacer** y que borrar es irreversible. Mostrar la posibilidad de borrar todo, sin ejecutarla sobre datos reales. Visitar Menú y editar un producto.

**3:25–4:15 | Rendimiento y persistencia (50 s)**

“SQLite almacena cambios incrementales en lugar de reescribir todo el JSON. El benchmark crea 100.000 registros: en nuestro entorno de referencia tardó ~33,52 segundos en registrarlos, y preparar uno a continuación ~0,40 ms. No son garantías universales. El servicio sigue cargando pedidos a memoria durante el reinicio, por lo que aún se debe mejorar el arranque para millones de registros.”

**4:15–4:40 | Pruebas y conclusión (25 s)**

Mostrar `py run_tests.py` con 24 pruebas aprobadas. Concluir que FoodQueue separa prioridades con arreglos, mantiene tiempos constantes amortizados para encolar y preparar, y documenta la diferencia entre costo en memoria y costo de almacenamiento.

**Nota del expositor:** grabar pantalla con reloj visible, verificar micrófono y comprimir la duración a **máximo 5:00**. El video no está incluido en la descarga; este archivo es su guion.
