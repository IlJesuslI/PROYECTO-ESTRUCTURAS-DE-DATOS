# Manual de usuario — FoodQueue v4

## Requisitos
Python 3.10+ y navegador actualizado; no requiere `pip install`.

## Ejecución
1. Extrae el ZIP.
2. Abre la carpeta `FoodQueue` en VS Code.
3. Ejecuta `py run_tests.py` y después `py server.py`.
4. Visita `http://127.0.0.1:8000`.

## Operación
1. **Menú:** agrega, edita o desactiva productos.
2. **Nuevo pedido:** selecciona cliente, artículos, cantidades y prioridad **Normal** o **Alta**.
3. **Pendientes:** se muestran según el turno efectivo de las dos colas.
4. **Preparar siguiente:** procesa el primer pedido elegible; no recorre todos los pedidos.
5. **Historial:** consulta los preparados y utiliza **Borrar último** para eliminar exclusivamente el preparado más reciente (LIFO); no existe **Deshacer** ni borrado total.

## Archivos y respaldo
Se utilizan `data/state.json` (base inicial) y `data/state.jsonl` (diario incremental). Conserva **ambos** archivos al actualizar. Para respaldarlos, detén el servidor y copia toda la carpeta `data/`. Estos archivos no se suben a GitHub.

**Si vienes de una versión con solo `state.sqlite3`, no elimines ese archivo**: esta versión no lo abre ni lo migra. Exporta primero los pedidos a JSON desde la versión anterior si deseas conservarlos.

## Pruebas y rendimiento
`py run_tests.py` ejecuta las pruebas; `py benchmark.py 100000` registra 100.000 pedidos de prueba en una carpeta temporal sin modificar los pedidos reales.
