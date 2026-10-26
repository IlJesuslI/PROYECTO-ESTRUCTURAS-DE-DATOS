# FoodQueue v4 — Sin base de datos SQL

Sistema local de pedidos de restaurante, construido con **Python 3.10+**, HTML, CSS y JavaScript. **No utiliza SQLite ni ninguna base de datos SQL**; conserva información en un archivo JSON inicial y un diario incremental JSONL.

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
- Historial de preparados en pila `list`, con opción **Borrar**, sin **Deshacer**.
- Guardado incremental en `data/state.jsonl`, una línea JSON por cambio, sin reescribir 100.000 registros en cada pedido.
- Consulta limitada de pendientes e historial.

## Persistencia

- `data/state.json`: estado inicial o archivo heredado.
- `data/state.jsonl`: eventos posteriores (creación, actualización, cancelación, preparación y borrado).
- Ambos archivos deben conservarse **juntos** y están excluidos de Git.
- Al reiniciar, el sistema reconstruye la memoria leyendo el JSON y reproduciendo el diario JSONL. El arranque empeora a medida que crece el diario; aún no se implementa compactación automática.
- **Migración importante:** si tu instalación anterior contiene únicamente `state.sqlite3`, **no se importa automáticamente**. Haz copia de seguridad antes de sustituir la versión. Para conservar esos registros se necesita exportarlos a JSON desde la versión anterior.

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
| Borrar historial completo | O(h) | O(1) evento, más serialización |
| Reiniciar | O(n log n + e) por ordenar pedidos y reproducir e eventos | Lectura O(tamaño total de archivos) |

`n` pedidos, `m` productos, `h` historial, `k` elementos solicitados, `e` eventos. El costo de escritura en disco depende del sistema de archivos, buffer y dispositivo. El proceso mantiene O(n) pedidos en memoria.

## Limitaciones

El diario JSONL es adecuado para demostración y uso local, pero **no es una base transaccional multiusuario**. Un corte de energía puede dejar una última línea incompleta; se ignora al iniciar. Un fallo de escritura puede dejar la RAM y el disco desincronizados. No abras dos servidores sobre los mismos archivos. Realiza copias de seguridad con el servidor detenido. No publiques el servidor en internet sin autenticación.

## Documentación

Consulta `docs/` para manual, API, estructura de datos, complejidad, riesgos, entrega académica y guion del video.
