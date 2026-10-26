# Riesgos, casos límite y escalabilidad — FoodQueue v3.0

## Objetivo

La sustitución de `heapq` por **dos arreglos (alta y normal)** permite seleccionar el siguiente pedido leyendo los frentes, sin recorrer la cola completa. SQLite almacena registros individualmente. Estas dos optimizaciones mejoran la atención cuando existe un historial grande, pero no garantizan latencia constante de disco.

## Riesgos y mitigaciones

| Riesgo | Comportamiento actual | Mitigación / mejora futura |
|---|---|---|
| 100.000 pedidos | Prueba de referencia satisfactoria, con arranque O(n log n) | Cargar en RAM solo pendientes para millones |
| Cancelaciones masivas | Marcado lógico, entradas obsoletas se saltan al desencolar | Compactación amortizada |
| Inanición de normales | Hasta tres altas consecutivas; siguiente normal si existe | Política configurada en el servicio |
| Duplicados de producto | Nombres activos duplicados rechazados | Validación actual O(m), índice por nombre para catálogos enormes |
| Cantidades malformadas | Rechaza negativas, decimales, bool, 0 por renglón, >99 por renglón | Mantener validación de API |
| Precio inválido | Solo entero positivo y ≤50.000.000 COP | Mantener límites de dominio |
| Producto inactivo | Prohibido agregar a pedidos nuevos | Preservar el nombre y precio histórico |
| Borrado accidental de historia | Diálogo de confirmación; DELETE definitivo | Roles/permisos, papelera temporal o auditoría en producción |
| Clientes antiguos con prioridad 2 | Migra registros existentes `2 → 1` en SQLite/JSON | Modificar integraciones para enviar solo 0/1 |
| Dos procesos del servidor a la vez | Bloqueo en memoria solo dentro del mismo proceso; SQLite coordina escrituras | Evitar múltiples instancias; coordinar con transacciones robustas si hay concurrencia multi-proceso |
| Historial demasiado grande en navegador | Páginas de 30, se cargan por demanda | Paginación por cursor a gran escala |
| Miles de pendientes | Se muestra como máximo 60 | Búsqueda/filtros y paginación para operaciones masivas |
| Corrupción/pérdida de disco | SQLite WAL y commit por operación | Backups regulares consistentes, monitoreo y restauración ensayada |
| Reiniciar con n registros | Lee y reconstruye O(n log n), usa O(n) RAM | Carga diferida, índices persistentes y colas solo activas |
| XSS en datos visibles | JS usa `textContent`, no interpola HTML del usuario | Mantener controles, usar CSP si se expone remotamente |
| Acceso por internet | No hay usuarios, autenticación, CSRF ni autorización | **NO exponer** sin seguridad adicional |
| Peticiones enormes | Tamaño máximo HTTP ~1 MB, límite de 50 líneas/500 unidades | Validación adicional por rol/negocio |
| Gran volumen de históricos al borrar | Operación masiva O(h), escrituras SQLite | Ejecutar en ventana de mantenimiento si volumen masivo |

## Riesgos de consistencia detectados y limitaciones conocidas

1. **Una sola instancia:** el servicio usa `RLock` para sincronizar hilos de *este proceso*. No garantiza consistencia si dos procesos independientes cargan las mismas colas a RAM y actualizan la misma SQLite. No ejecutar servidores dobles.
2. **Estado RAM previo a fallo de disco:** el flujo normal modifica estructuras en memoria y luego confirma SQLite. Si falla la persistencia (disco lleno, I/O), la memoria podría quedar desincronizada. En producción se recomienda construir operaciones transaccionales con rollback del estado en memoria y supervisión de fallos.
3. **Borrado irreversible:** en caso de confirmar DELETE sin copia de seguridad, no existe recuperación por «Deshacer».
4. **Reinicio con datos grandes:** la reconstrucción no es O(1), aunque preparar un pedido sí sea O(1) amortizado en memoria.
5. **Paginación OFFSET:** páginas muy lejanas pueden ralentizarse, especialmente con millones de preparados. Se recomienda keyset pagination por `stack_seq`.
6. **Benchmark no simula tráfico concurrente:** las pruebas descritas ejecutan escrituras secuenciales con un producto. Medir p95/p99 y solicitudes concurrentes es trabajo futuro.

## Evaluación de 100.000 pedidos

En prueba local orientativa con `benchmark.py 100000`:

- Registro total: **33,522 s** para 100.000 pedidos.
- Promedio: **0,3352 ms/registro**.
- Preparar siguiente después del registro masivo: **0,4016 ms**.
- Consulta de indicadores: **0,0074 ms**.
- Base SQLite principal: **55.236 KiB**, excluyendo otros archivos temporales.

No se debe extrapolar el promedio como tiempo del pedido número 100.000 sin medirlo individualmente. Y los resultados no son equivalentes a los tiempos de un equipo Windows distinto.

## Estrategia para pruebas adicionales

Ejecutar con 1.000, 10.000, 50.000 y 100.000 pedidos; repetir varias veces y reportar mediana y percentil 95. Medir por separado altas, extracciones, cancelaciones, borrado y reinicio. La optimización siguiente debe centrarse en evitar cargar todo el historial durante el arranque y separar índices de pendientes de los registros históricos.
