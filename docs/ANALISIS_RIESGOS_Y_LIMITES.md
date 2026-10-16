# Análisis de errores, límites y comportamiento con muchos datos

## Resumen

La lógica de las estructuras es eficiente para un proyecto académico y para una operación pequeña/mediana en una sola máquina. El principal límite no está en `deque` o `heapq`, sino en la persistencia JSON completa, que reescribe todos los registros después de cada cambio.

## Casos de entrada controlados

- Nombre de producto vacío o mayor a 80 caracteres → rechazado.
- Cliente vacío o mayor a 80 caracteres → rechazado.
- Precio no entero, cero, negativo o mayor a COP 50.000.000 → rechazado.
- Cantidad no entera, menor a 1 o mayor a 99 por línea → rechazada.
- Más de 50 líneas distintas en un pedido → rechazado.
- Más de 500 unidades totales → rechazado.
- Producto inexistente/inactivo → rechazado.
- Producto activo duplicado por nombre (sin distinguir mayúsculas/minúsculas) → rechazado.
- Prioridad fuera de 0, 1 o 2 → rechazada.
- JSON inválido, cuerpo vacío, no UTF-8 o mayor a 1 MB → rechazado por la API.
- Preparar cuando no hay pedidos → devuelve error controlado.
- Cancelar un pedido ya preparado/cancelado → devuelve conflicto controlado.

## Riesgos mitigados

### Dinero
Se usan **pesos colombianos enteros**, no `float`; por tanto se evitan errores típicos de precisión binaria como 0.1 + 0.2.

### Historial
El pedido guarda una copia del nombre y precio unitario del producto al momento de comprar. Cambiar el menú después no altera pedidos anteriores.

### Eliminación de productos
Es lógica y no física; evita referencias rotas en el historial.

### Corrupción parcial del archivo
El programa escribe primero `state.json.tmp` y luego usa `os.replace`, reduciendo el riesgo de dejar un JSON parcialmente escrito si ocurre un fallo durante el guardado.

### Cancelaciones dentro de colas
Se usa eliminación perezosa. El pedido cambia de estado y, cuando su ID llega al frente del `deque`/heap, se ignora si ya no está pendiente. Esto evita búsquedas O(n) dentro de las estructuras.

### Inanición por prioridad
Máximo 3 pedidos prioritarios consecutivos si existen normales esperando.

## Qué puede fallar con MUCHOS datos

### 1. Archivo JSON muy grande — riesgo principal
Cada alta, cancelación o preparación serializa nuevamente productos + todos los pedidos. Con decenas o cientos de miles de pedidos, la latencia y uso de memoria aumentarán de forma lineal.

**Escalamiento recomendado:** migrar persistencia a SQLite para un solo equipo o PostgreSQL para varios usuarios, manteniendo en memoria `deque`, `heapq` y la pila solo para pedidos activos.

### 2. Memoria RAM
Todos los pedidos se mantienen en el diccionario `orders`, y las estructuras activas están en memoria. Con millones de pedidos, no es adecuado.

**Mejora:** archivar pedidos preparados antiguos en base de datos y mantener en RAM solo una ventana reciente.

### 3. Un solo proceso
`RLock` protege hilos del mismo proceso, pero no coordina dos instancias independientes de `server.py` escribiendo el mismo archivo.

**Regla:** ejecutar una sola instancia. Para despliegue real, usar base de datos transaccional.

### 4. Durabilidad frente a fallo eléctrico extremo
`os.replace` evita archivos parciales, pero no garantiza por sí solo sincronización física (`fsync`) ante pérdida instantánea de energía.

**Mejora:** base de datos con WAL/journaling o añadir `fsync` al archivo y directorio.

### 5. Prioridades mal usadas
Si un usuario marca todo como “urgente”, la prioridad pierde significado. El algoritmo no puede inferir si la prioridad es legítima.

**Mejora:** restringir el permiso de asignar prioridad o registrar auditoría.

### 6. Cantidades duplicadas desde un cliente manipulado
La API consolida líneas repetidas por `product_id` y vuelve a validar el total. No confía solo en JavaScript.

### 7. Texto malicioso / XSS
La interfaz genera los textos con `textContent`, no con `innerHTML`, por lo que nombres como `<script>` se muestran como texto y no se ejecutan. El backend también limita longitud y caracteres de control.

### 8. IDs falsos
Los endpoints de producto/pedido aceptan UUIDs con patrón esperado y luego verifican existencia. No se confía en IDs enviados por el navegador.

## Prueba de carga sugerida para la sustentación

Puede generarse un script que cree 1.000, 10.000 y 50.000 pedidos y mida: tiempo de inserción, tamaño del archivo y tiempo de reinicio. La predicción es que `heapq` y `deque` seguirán respondiendo eficientemente, pero el guardado JSON dominará el tiempo total conforme crezca el dataset.

## Conclusión técnica

Para la entrega universitaria, la solución está optimizada en las operaciones centrales de las estructuras. Para producción con alta concurrencia o cientos de miles de registros, la optimización correcta no consiste en cambiar `deque`/`heapq`, sino en sustituir la persistencia monolítica JSON por una base de datos transaccional y separar historial de estado activo.

## Medición de referencia realizada sobre esta versión

En una ejecución de validación del proyecto, incluyendo escritura real de `state.json`, se obtuvo:

| Pedidos creados | Tiempo total | Promedio por pedido | Tamaño JSON |
|---:|---:|---:|---:|
| 100 | 0,056 s | 0,56 ms | 39,1 KiB |
| 500 | 0,764 s | 1,53 ms | 194,1 KiB |
| 1.000 | 2,912 s | 2,91 ms | 387,9 KiB |

Estos valores son **referenciales**, no una garantía de rendimiento: dependen del procesador, el disco, el sistema operativo y la carga del equipo. La tendencia creciente confirma que la reescritura completa del JSON se convierte progresivamente en el cuello de botella.
