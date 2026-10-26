# FoodQueue

Nuestro sistema consiste en una aplicación web local que permite gestionar las funciones básicas de un restaurante, como administrar el menú y registrar pedidos con diferentes productos, cantidades y prioridades. Emplea estructuras de datos como **arreglos dinámicos, colas FIFO, colas con prioridad y pilas**. Además, evita que los pedidos normales sean desatendidos frente a los prioritarios, permite consultar el historial y deshacer el último pedido preparado.
- Interfaz hecha en JavaScript, HTML y CSS.
- Lógica y procesamiento con Python.

## Inicio rápido

```powershell
py run_tests.py
py benchmark.py 100000
py server.py
```

Abre `http://127.0.0.1:8000`.

## Funcionalidades

- Menú editable con arreglo dinámico `list`.
- Dos prioridades: **Normal (0)** y **Alta (1)**, implementadas mediante **dos arreglos con índice de cabeza**, no con `heapq`.
- Selección O(1) del arreglo a atender, con equidad: hasta tres pedidos altos consecutivos si hay normales esperando.
- Cancelación por identificador, sin búsqueda lineal en la cola.
- Historial de preparados en pila `list`, con opción **Borrar último** (LIFO), sin **Deshacer** ni borrado total.
- Guardado incremental en `data/state.jsonl`, una línea JSON por cambio, sin reescribir 100.000 registros en cada pedido.
- Consulta limitada de pendientes e historial.

## Complejidad principal

| Operación | Costo de estructura en RAM | Persistencia |
|---|---|---|
| Agregar producto | O(1) amortizado, comprobación de nombre O(m) | O(tamaño del evento) |
| Crear pedido | O(k) por k líneas de productos; encolar O(1) amortizado | O(tamaño del pedido) |
| Elegir prioridad | O(1) | — |
| Extraer pedido | O(1) amortizado, O(c) puntual si salta c cancelados | O(tamaño del evento) |
| Cancelar por ID | O(1) esperado | O(tamaño del evento) |
| Consultar estado | O(m) por productos activos; O(1) por contadores | — |
| Listar k pendientes | O(k + c) con c cancelados saltados | — |
| Historial, página de k tras offset | O(offset + k + tombstones) | — |
| Borrar último preparado | O(1) amortizado | O(b) por evento JSONL |
| Reiniciar | O(n log n + e) por ordenar pedidos y reproducir e eventos | Lectura O(tamaño total de archivos) |

`n` pedidos, `m` productos, `h` historial, `k` elementos solicitados, `e` eventos. El costo de escritura en disco depende del sistema de archivos, buffer y dispositivo. El proceso mantiene O(n) pedidos en memoria.

## Porcentaje de IA

La versión entregada como base fue generada aproximadamente en **90 % con asistencia de inteligencia artificial** y en **10 % mediante definición/selección humana del problema, requisitos, validación y ajustes de presentación**.


## Hecho por:
- Jesus David Muñoz Gomez
- Edwin Mauricio Cifuentes Monterrey
- Jacobo Atahualpa Manrique Monroy