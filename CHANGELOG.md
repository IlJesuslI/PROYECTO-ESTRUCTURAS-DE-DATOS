# Registro de cambios

## v4.0 — Sin SQL
- Eliminado el uso de SQLite del servicio, las pruebas y el benchmark.
- Persistencia mediante archivo JSON inicial y diario JSONL incremental.
- Conservadas dos prioridades, dos arreglos con índices de cabeza, pila de historial y borrado.
- Actualizada la documentación y las advertencias de migración.

## v3.0
- Dos colas por arreglos, prioridades Alta/Normal y rediseño de interfaz.
