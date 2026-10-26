# Documento para entrega universitaria — FoodQueue v3.0

## Problema y objetivo

Gestionar el menú, registro, preparación y seguimiento de pedidos de un restaurante. Se busca demostrar, a través de acciones observables en la interfaz, el funcionamiento y complejidad de varias **estructuras lineales**, priorizando un rendimiento adecuado aun con decenas de miles de pedidos.

## Tecnologías

- Python 3.10+: backend HTTP, modelos, algoritmo, pruebas y persistencia `sqlite3`.
- HTML, CSS y JavaScript: interfaz web local adaptable.
- SQLite: guardado incremental sin dependencias externas.
- Git / GitHub: control de versiones, documentación y colaboración del equipo.

## Estructuras justificadas

1. **Arreglo dinámico (`list`)**: catálogo de productos de tamaño variable.
2. **Cola normal (`ArrayQueue` sobre `list`)**: atención FIFO mediante índice, evitando `pop(0)`.
3. **Cola con prioridad mediante arreglos**: separación directa en arreglos Alta y Normal; selección del siguiente en O(1), extracción O(1) amortizado.
4. **Pila (`list`)**: registra el orden LIFO de preparación; historial desde el más reciente. Eliminar una entrada individual no equivale a pop; no existe deshacer.

Los diccionarios son índices auxiliares y SQLite es persistencia, no reemplazos de las estructuras anteriores.

## Funcionalidades terminadas

- Menú: crear, editar, desactivar, consultar productos.
- Pedidos: cliente, ítems, cantidades, totales COP, prioridad **Normal** o **Alta**.
- Atención: hasta tres altos seguidos si hay normales en espera.
- Cancelaciones de pedidos pendientes.
- Historial: consulta paginada, **Borrar** por pedido, **Borrar historial**.
- Migración de prioridades antiguas y de un archivo JSON legado.
- API HTTP documentada, 24 pruebas automáticas y benchmark de 100.000 registros.

## Complejidad principal

| Función | Costo en RAM |
|---|---|
| Insertar objeto en arreglo de prioridad | O(1) amortizado |
| Escoger prioridad | O(1) |
| Extraer pedido (con descartes perezosos) | O(1) amortizado |
| Cancelar por ID | O(1) esperado |
| Consultar contadores | O(1) |
| Consultar `k` pendientes | O(k), después de SQL indexado |
| Borrar todo el historial | O(h) |
| Reiniciar/reordenar colas | O(n log n) |

Se detallan casos peor y amortizado, y efectos de SQLite, en `COMPLEJIDAD_ALGORITMICA.md`.

## Evidencia de pruebas

- 24 casos automatizados finalizados correctamente en esta entrega.
- Ejecución de 100.000 inserciones de prueba: 33,522 s en entorno Linux, promedio 0,3352 ms por inserción; una preparación posterior 0,4016 ms. Los valores difieren en Windows.

## Asistencia de IA y responsabilidades

La asistencia de IA se estima provisionalmente en **~90 % del código base y adaptación de esta versión**. El equipo debe comprobar/actualizar ese valor conforme a sus aportes reales, dejar constancia de revisión manual, pruebas, commits y responsabilidades. No es una cifra medida automáticamente.

## Entregables

1. Repositorio GitHub con código fuente, licencia, `.gitignore`, pruebas y documentación.
2. Manual `MANUAL_USUARIO.md`.
3. Explicación de estructuras `ESTRUCTURAS_DATOS.md`.
4. Análisis de complejidad `COMPLEJIDAD_ALGORITMICA.md`.
5. Informe de riesgos `ANALISIS_RIESGOS_Y_LIMITES.md`.
6. Guion de presentación `GUION_VIDEO_5_MIN.md` para grabación **máximo 5 minutos**.

**Pendiente externo:** publicar realmente estos archivos y grabar el video. El ZIP no equivale a un push a GitHub ni a un video terminado.
