# Historial de versiones

## v3.0 — Prioridad implementada con arreglos

- Remplazado `heapq` por `ArrayQueue` con `list` + `head`.
- Dos colas independientes: Normal (`0`) y Alta (`1`).
- Eliminación de Urgente (`2`), migración automática en SQLite y JSON.
- Eliminación total de operación y endpoint de deshacer.
- Nuevos endpoints DELETE de historial individual y completo.
- Datos paginados, consultas con índices SQLite, contadores en RAM.
- Frontend renovado en diseño y navegación (Pedidos / Menú / Historial).
- 24 pruebas y documentos técnicos reescritos con análisis de complejidad.

## v2.x — Optimización SQLite anterior

- Persistencia incremental SQLite, prioridad Normal/Alta/Urgente y cola `heapq`.
