# FoodQueue v3.0 — Sistema de pedidos de restaurante

Aplicación académica de gestión de pedidos con **Python**, **JavaScript**, **HTML**, **CSS** y **SQLite**. Demuestra estructuras lineales y un esquema eficiente de prioridad implementado mediante **dos arreglos dinámicos de referencias a pedidos con índices de cabeza**. No requiere paquetes de terceros.

## ¿Qué cambió en v3?

- Solo existen **Normal (`0`)** y **Alta (`1`)**. Se eliminó **Urgente**.
- Cola con prioridad implementada usando **dos arreglos de objetos `Order`**: `high_queue` y `normal_queue`; sin `heapq` ni recorridos globales de pedidos para atender el siguiente.
- Extracción desde la cabeza mediante un índice, **O(1) amortizado**. Los elementos cancelados se omiten de forma perezosa.
- Regla de equidad: hasta tres pedidos altos seguidos; si hay normales, el siguiente será normal.
- Historial sin “Deshacer”: ahora permite **Borrar** individualmente o **Borrar historial** completo (irreversible).
- Se quitó la sección visible «Estructuras»; la explicación técnica queda disponible en `docs/`.
- Interfaz rediseñada: navegación lateral, indicadores, prioridades visibles y pantallas adaptables.
- Estadísticas calculadas con contadores O(1) respecto a pedidos; pendientes e historial con consultas SQLite paginadas.
- Migración automática de SQLite anterior (prioridad `2` pasa a `1`) y de JSON si todavía no existe una base SQLite.

## Instalación y ejecución (Windows / VS Code)

Requisitos: **Python 3.10 o superior**.

```powershell
py --version
py run_tests.py
py server.py
```

Abrir **http://127.0.0.1:8000**. Si tu entorno usa `python` en vez de `py`, reemplaza el prefijo. Para detener, `Ctrl + C`.

```powershell
py benchmark.py 100000
```

> IMPORTANTE antes de actualizar: detén el servidor y **haz copia de seguridad de la carpeta `data/` completa**, incluidos `state.sqlite3`, `state.sqlite3-wal` y `state.sqlite3-shm` si existen. No copies bases activas mientras se están escribiendo. Conserva tu `data/` al actualizar archivos del proyecto. No subas esta carpeta a GitHub.

### Actualizar tu proyecto local desde esta versión

1. Detén `py server.py`.
2. Crea una copia del directorio actual del proyecto y del directorio `data/`.
3. Extrae esta carpeta sobre una **copia de trabajo** del repositorio y revisa `git diff` antes de confirmar cambios.
4. Conserva la base SQLite de tu instalación anterior, no la reemplaces por una vacía.
5. Ejecuta `py run_tests.py` (usa bases temporales, no modifica tus pedidos).
6. Inicia `py server.py`. La primera ejecución convierte automáticamente las antiguas prioridades 2 a 1.
7. Si tienes cambios propios en GitHub, intégralos manualmente antes de subir: esta entrega se preparó con la última copia local disponible y **no confirma el contenido remoto actual**.

## Estructuras de datos

| Estructura académica | Implementación | Uso |
|---|---|---|
| Arreglo dinámico | `list[Product]` | Menú |
| Cola FIFO | `ArrayQueue` sobre `list[Order]` + índice de cabeza | Pedidos normales |
| Cola con prioridad por arreglos | Dos `ArrayQueue`: alta y normal | Política de turnos |
| Pila | `list[str]` con `append` | Últimos preparados e historial inverso |

Un `dict[str, Order]` funciona como **índice auxiliar** para obtener pedidos por ID sin recorrerlos. SQLite es la persistencia duradera y no reemplaza la demostración de estructuras académicas.

**Atención al detalle:** la pila mantiene el orden LIFO de preparación, pero ya **no se ofrece un `pop` de deshacer**. El borrado individual deja temporalmente una entrada inválida que se limpia en una compactación eventual, evitando la búsqueda lineal por cada eliminación.

## Complejidad algorítmica (RAM, antes de I/O)

Sean `n` los pedidos activos, `m` los productos, `k` los resultados solicitados y `h` los pedidos preparados.

| Operación | Complejidad |
|---|---|
| Añadir a cola normal / alta | **O(1) amortizado** |
| Preparar siguiente (elegir / extraer) | **O(1) amortizado** |
| Cancelar pedido por ID | **O(1)** |
| Ver contadores de pedidos | **O(1)** |
| Registrar pedido (validación de `r` renglones) | **O(r)**, más persistencia |
| Añadir producto al menú | **O(m)** por validación de nombre duplicado |
| Editar o desactivar producto | **O(m)** por validación/búsqueda de posición |
| Añadir elemento a pila de preparados | **O(1)** |
| Borrar un registro del historial por ID | **O(1) amortizado** en RAM, más operación SQLite |
| Borrar el historial completo | **O(h)** |
| Reiniciar y reconstruir colas desde SQLite | **O(n log n)** por ordenamiento; **O(n)** en memoria |

**SQLite:** índices B-tree, aproximadamente `O(log n)` para localizar/actualizar filas (además de la escritura física). Listados limitados: aproximadamente `O(log n + k)` sin desplazamiento, y `O(log n + offset + k)` con `OFFSET`. La duración efectiva varía según disco, transacciones y caché.

Más detalle: [ESTRUCTURAS_DATOS.md](docs/ESTRUCTURAS_DATOS.md) y [COMPLEJIDAD_ALGORITMICA.md](docs/COMPLEJIDAD_ALGORITMICA.md).

## Pruebas y rendimiento

```powershell
py run_tests.py
py benchmark.py 10000
py benchmark.py 100000
```

**Verificado en el entorno de elaboración:** 24 pruebas unitarias correctas. Benchmark de creación de 100.000 pedidos: **33,522 s** en total (~**0,3352 ms/registro**); preparación del siguiente pedido con esos registros: **0,4016 ms**; estado: **0,0074 ms**. Son mediciones de referencia de un entorno Linux, no garantías de tu Windows ni comparaciones controladas con pruebas anteriores.

## Estructura del repositorio

```text
FoodQueue/
├── app/
│   ├── models.py
│   └── service.py           # cola por arreglos, pila, validación y SQLite
├── static/
│   ├── index.html           # interfaz renovada
│   ├── app.js
│   └── styles.css
├── data/                     # persistencia local; ignorada por Git
├── tests/test_service.py    # 24 pruebas
├── docs/
│   ├── MANUAL_USUARIO.md
│   ├── ESTRUCTURAS_DATOS.md
│   ├── COMPLEJIDAD_ALGORITMICA.md
│   ├── ANALISIS_RIESGOS_Y_LIMITES.md
│   ├── API.md
│   ├── INDICE_FUNCIONAMIENTO.md
│   ├── ENTREGA_PROYECTO.md
│   └── GUION_VIDEO_5_MIN.md
├── server.py
├── benchmark.py
└── run_tests.py
```

## Seguridad y límites

Aplicación de demostración **local** sin usuarios ni autenticación. El servidor escucha `127.0.0.1` por defecto y los datos se almacenan localmente. No la expongas a internet ni a una red compartida sin añadir autenticación, autorización, registro de auditoría, protección contra solicitudes maliciosas y copias de seguridad. `SQLite` resuelve el guardado incremental, pero esta aplicación aún carga en memoria los pedidos durante el arranque: memoria **O(n)**; no promete escalar sin cambios a millones de pedidos.

## Participación de IA

El código base y esta actualización fueron realizados mayoritariamente con herramientas de inteligencia artificial. Como declaración académica provisional, se estima **90 % de asistencia IA** en la generación/adaptación del código. Este porcentaje es estimativo, no una medición automática de líneas, y debe revisarse y ajustarse al incorporar aportes propios o del equipo. Las decisiones de alcance y la validación final corresponden al equipo del proyecto.

## Documentación complementaria

- [Manual](docs/MANUAL_USUARIO.md) · [Índice de funcionamiento](docs/INDICE_FUNCIONAMIENTO.md)
- [Estructuras](docs/ESTRUCTURAS_DATOS.md) · [Complejidad](docs/COMPLEJIDAD_ALGORITMICA.md)
- [Riesgos y escalabilidad](docs/ANALISIS_RIESGOS_Y_LIMITES.md) · [API](docs/API.md)
- [Documento de entrega](docs/ENTREGA_PROYECTO.md) · [Guion del video](docs/GUION_VIDEO_5_MIN.md)
