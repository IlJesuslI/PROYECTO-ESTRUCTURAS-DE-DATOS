# Complejidad algorítmica — FoodQueue v4 (JSON + JSONL)

## Notación

- `n`: pedidos cargados; `m`: productos; `h`: preparados; `k`: tamaño de un pedido o listado; `e`: eventos del diario; `c`: entradas canceladas saltadas.
- Los costos de `dict` son esperados (tabla hash), no garantías de peor caso.
- Los arreglos usan `append` e índices de cabeza. La compactación por mitades cuesta O(n) puntualmente y O(1) amortizado por extracción.

| Operación | Tiempo RAM | Espacio adicional |
|---|---|---|
| Insertar al final de arreglo | O(1) amortizado | O(1) amortizado |
| Elegir cola Normal/Alta | O(1) | O(1) |
| Extraer frente | O(1) amortizado; O(c) puntual | O(1) amortizado |
| Cancelar por ID | O(1) esperado | O(1) |
| Crear pedido | O(k) + O(1) amortizado para cola | O(k) |
| Agregar producto | O(m) para validar nombre | O(1) |
| Historial: apilar | O(1) amortizado | O(1) |
| Borrar último preparado (pop LIFO) | O(1) amortizado; puede saltar marcas antiguas | O(1) |
| Mostrar k pendientes | O(k+c) | O(k) |
| Historial paginado | O(offset+k+tombstones) | O(k) |
| Estado / estadísticas | O(m) productos; contadores O(1) | O(1) |
| Reconstrucción al iniciar | O(n log n + e) | O(n) |

## Costos de almacenamiento

Cada operación que modifica datos añade un **evento JSONL**. La escritura requiere serializar ese evento, no el historial completo. El costo es O(b) para b bytes del evento y crece el espacio en disco O(suma de tamaños de eventos). El reinicio reproduce los `e` eventos, por lo que su tiempo sí aumenta con el historial de cambios. No hay compactación automática del diario.

## Benchmark local de referencia

En el entorno donde se generó esta entrega, 100.000 registros tardaron **3,667 s** en total; preparar el siguiente tardó **0,272 ms**. Son mediciones de referencia, **no garantías** de rendimiento en Windows ni de durabilidad ante apagones.
