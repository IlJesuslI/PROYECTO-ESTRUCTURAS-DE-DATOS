# Análisis de complejidad algorítmica — FoodQueue v3.0

## Convenciones

`n`: total de pedidos cargados en memoria; `p`: pendientes; `h`: preparados; `m`: productos del menú; `r`: líneas de un pedido (máximo 50); `k`: elementos devueltos a la UI (máximo 200), `o`: OFFSET de consulta histórica.

Distinguir **complejidad algorítmica en memoria** de **persistencia SQLite en disco**. Los valores asintóticos no equivalen directamente a milisegundos; SQLite usa B-trees y I/O transaccional.

## Tabla de operaciones

| Operación | En memoria | En disco / efecto relevante | Justificación |
|---|---|---|---|
| Insertar pedido normal | O(r) + O(1) amortizado | Escritura/indexado aprox. O(log n) | Validación r, lista.append |
| Insertar pedido alta | O(r) + O(1) amortizado | Escritura/indexado aprox. O(log n) | Mismo arreglo distinto |
| Decidir siguiente cola | O(1) | Ninguno | Comprueba contadores y racha |
| Extraer pedido | O(1) amortizado | Actualiza una fila aprox. O(log n) | Índice head + compactación |
| Cancelar pedido | O(1) esperado | Actualiza una fila aprox. O(log n) | Diccionario y lazy deletion |
| Guardar preparado en pila | O(1) amortizado | Persistencia incluida en extracción | list.append |
| Borrar preparado por ID | O(1) amortizado | DELETE indexado aprox. O(log n) | No busca en pila, compacta ocasionalmente |
| Borrar historial completo | O(h) en RAM | O(h) filas eliminadas | Eliminación masiva intencional |
| Consultar contadores de pedidos | O(1) | Ninguno | `_counts` |
| Contar productos activos | O(m) | Ninguno | `sum` del menú |
| Mostrar k pendientes | O(k) en la combinación | Aproximadamente O(log n + k) por índice | Dos SELECT limitados y combinación |
| Mostrar k históricos desde offset o | O(k) conversión JSON | Aproximadamente O(log n + o + k) | Índice por `stack_seq` y OFFSET |
| Buscar producto por ID | O(1) esperado | Ninguno | Índice dict |
| Detectar nombre de producto repetido | O(m) | Ninguno | Comparación de nombres |
| Actualizar precio de producto | O(m) | Una fila | Posición en lista y duplicados |
| Reiniciar/reconstruir colas | O(n log n) | O(n) lectura de base | Ordenamiento por secuencia |
| Memoria de ejecución | O(n + m + h) | O(n) almacenado SQLite | Índices y estructuras vivas |

Nota: el orden de variables es una simplificación. El propio costo físico de serializar un pedido también depende del tamaño de su contenido, y tiempos de commit/flushing dependen del dispositivo y del modo de SQLite.

## Prueba formal: FIFO mediante arreglos

Una cola `ArrayQueue` almacena `buffer: list[Order]` y `head`:

- `push`: `append` es O(1) amortizado.
- `pop`: incrementa `head`; cada elemento se visita como máximo una vez al ser procesado o descartado.
- Compactación: cuando `head >= len(buffer)/2`, copiar el sufijo vivo cuesta O(s), pero antes debieron consumirse al menos O(s) elementos; el coste agregado se reparte y da O(1) amortizado por extracción.

En la **peor extracción aislada** pueden saltarse `c` cancelaciones consecutivas: coste O(c) para esa operación, no O(1) peor caso. Sobre toda la secuencia de extracciones el costo de esos saltos es lineal en el número de entradas consumidas.

## Prueba: planificación de prioridad

No se ordena todo el conjunto de pendientes para escoger. Hay dos contadores activos y una racha `consecutive_priority`:

```text
si alta > 0 y (normal == 0 o racha_alta < 3): elegir alta
si no: elegir normal
extraer de frente mediante índice
```

La **selección** es O(1). Esto se logra porque el único dominio de prioridad válido contiene exactamente dos valores (0 y 1). Para muchos niveles dinámicos se necesitaría una implementación distinta.

## ¿Dónde siguen existiendo costos grandes?

1. Al **iniciar** se cargan los pedidos en memoria desde SQLite y se ordenan las posiciones de cola; coste de arranque O(n log n) y RAM O(n).
2. La **base de datos** no ofrece O(1) garantizado por commit: buscar/escribir índices B-tree es aproximadamente O(log n), con fsync y mantenimiento de WAL.
3. `list_pending_orders()` consulta como máximo `k` de cada tipo, evitando ordenar el historial completo.
4. `list_history(limit, offset)` es paginado; con offsets muy grandes hay sobrecosto de salto `O(offset)`. Para millones conviene **paginación por cursor** usando `stack_seq`.
5. `clear_history()` es intencionalmente O(h); no se debe presentar como operación constante.
6. La vista del navegador crea `O(k)` nodos y consume `O(k)` memoria para cada lista visible.

## Resultados de benchmark

Entorno local de desarrollo (Linux, una sola prueba de referencia, `benchmark.py 100000`):

| Indicador | Resultado |
|---|---:|
| Pedidos registrados | 100.000 |
| Tiempo acumulado de registro | 33,522 s |
| Promedio registro | 0,3352 ms |
| Preparar un pedido con 100.000 creados | 0,4016 ms |
| Consultar indicadores | 0,0074 ms |
| Base SQLite principal | 55.236 KiB |

Estas cifras son **observaciones**, no promesas de rendimiento. El benchmark mide registros repetidos con un solo producto; no mide múltiples terminales simultáneas ni solicitudes de red. Repite en tu equipo Windows para resultados propios.

## Evolución para >1 millón de registros

Mantener solo IDs pendientes y recientemente preparados en RAM; recuperar el resto bajo demanda desde SQLite, añadir paginación basada en cursor y pruebas de concurrencia con bloqueos transaccionales. Para varios servidores, migrar a PostgreSQL/Redis y una coordinación multiusuario apropiada.
