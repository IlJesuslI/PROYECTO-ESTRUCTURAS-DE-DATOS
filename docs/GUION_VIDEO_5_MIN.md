# Guion para video de sustentación — máximo 5 minutos

## 0:00–0:30 — Presentación

“Hola. Este proyecto se llama **FoodQueue** y es un sistema de gestión de pedidos para restaurante. Su objetivo es demostrar el uso real de cuatro estructuras de datos lineales: arreglo dinámico, cola FIFO, cola con prioridad y pila. La lógica está desarrollada en Python y la interfaz web en HTML, CSS y JavaScript.”

## 0:30–1:10 — Arquitectura

Mostrar la pestaña **Estructuras**.

“Para el menú uso una lista de Python como arreglo dinámico. Los pedidos normales usan `deque`, porque permite insertar al final y retirar al principio en O(1). Los pedidos altos y urgentes usan `heapq`, con inserción y extracción O(log n). Finalmente, el historial de preparados funciona como una pila LIFO usando `append` y `pop`.”

## 1:10–2:10 — Menú y creación de pedido

Ir a **Menú**, crear un producto y volver a **Pedidos**.

“El menú puede crecer sin un tamaño fijo. Al crear un pedido, el backend valida cliente, prioridad, productos, cantidades y precios. El pedido guarda el precio del momento para que una modificación futura del menú no altere el historial.”

Crear un pedido normal y luego uno urgente.

## 2:10–3:05 — Colas y prioridad

“Los pedidos normales respetan FIFO. Los prioritarios se almacenan en un heap. Si hay igualdad de prioridad, se conserva el orden de llegada usando el número secuencial del pedido. Además, agregué una política de equidad: después de tres pedidos prioritarios consecutivos se procesa uno normal si existe, evitando inanición.”

Presionar **Preparar siguiente** y mostrar que sale primero el urgente.

## 3:05–3:40 — Pila y deshacer

Entrar en **Historial**.

“Cada pedido preparado se apila. Por eso el más reciente aparece primero. La opción Deshacer realiza un `pop` y devuelve ese pedido a su cola original. Esto demuestra de forma funcional el comportamiento LIFO.”

Hacer clic en **Deshacer último**.

## 3:40–4:25 — Validaciones y persistencia

“Los datos se persisten en JSON mediante reemplazo atómico para reducir riesgo de corrupción parcial. La interfaz no confía en el navegador: las validaciones se repiten en Python. Se controlan cantidades, precios, productos inactivos, duplicados, peticiones demasiado grandes y estados inválidos.”

Mostrar `python run_tests.py` en la terminal.

## 4:25–4:50 — Limitaciones

“Para un proyecto académico el rendimiento es adecuado. `deque` y `heapq` escalan bien, pero con cientos de miles de registros el cuello de botella sería reescribir el JSON completo. Para producción migraría la persistencia a SQLite o PostgreSQL y mantendría en memoria solo los pedidos activos.”

## 4:50–5:00 — IA

“Esta versión base fue desarrollada aproximadamente en un 90 % con asistencia de inteligencia artificial. El porcentaje debe actualizarse si realizo modificaciones adicionales antes de entregar.”
