# Estructuras lineales implementadas

1. **Arreglo dinámico** `products: list[Product]`: administra el catálogo. Alta con `append` O(1) amortizado; búsqueda de nombre O(m).
2. **Cola FIFO mediante arreglo** `normal_queue: ArrayQueue`: `items` e índice `head`; evita `pop(0)`. Inserción y extracción O(1) amortizado.
3. **Cola de prioridad mediante dos arreglos** `high_queue` y `normal_queue`: cada arreglo mantiene FIFO, y un contador elige cuál atender. Prioridades: 0 Normal, 1 Alta. No utiliza `heapq`; elegir el siguiente arreglo es O(1). Cada tres altos se atiende un normal si está esperando.
4. **Pila** `prepared_stack: list[str]`: registra los preparados en orden de inserción (`append` O(1) amortizado). La vista recorre el orden inverso. El borrado arbitrario no es una operación LIFO: se usa índice auxiliar por ID y marcas obsoletas con compactación ocasional.

Los diccionarios `orders` y `_product_index` son índices auxiliares para localizar objetos; no reemplazan las estructuras académicas. El diario JSONL conserva operaciones entre ejecuciones; no participa en la selección de prioridad.
