# FoodQueue 🍔

Sistema web local para administrar el menú y los pedidos de un restaurante mientras demuestra, de forma funcional, el uso de **arreglos dinámicos, colas FIFO, colas con prioridad y pilas**.

## Características

- Menú de productos: crear, consultar y desactivar.
- Pedidos con productos y cantidades.
- Prioridades: normal, alta y urgente.
- Procesamiento automático del siguiente pedido.
- Política anti-inanición: después de 3 prioritarios consecutivos se atiende 1 normal, si existe.
- Historial de preparados en pila y función **Deshacer último**.
- Persistencia automática en `data/state.json`.
- Interfaz web responsive en JavaScript puro.
- Servidor HTTP en Python, sin dependencias externas.
- Pruebas unitarias con `unittest`.

## Estructuras de datos

| Estructura | Implementación Python | Uso | Operación principal |
|---|---|---|---|
| Arreglo dinámico | `list` | Menú de productos | `append` amortizado O(1) |
| Cola | `collections.deque` | Pedidos normales | `append` / `popleft` O(1) |
| Cola con prioridad | `heapq` | Pedidos alta/urgente | push/pop O(log n) |
| Pila | `list` | Historial de preparados | `append` / `pop` O(1) |

> Los diccionarios que aparecen en el servicio son índices auxiliares para acceso O(1) por ID y no reemplazan las estructuras lineales evaluadas.

## Ejecutar

Requisito: Python 3.10 o superior.

```bash
python server.py
```

Abrir en el navegador:

```text
http://127.0.0.1:8000
```

No se requiere `pip install`.

## Ejecutar pruebas

```bash
python run_tests.py
```

## Estructura del repositorio

```text
FoodQueue/
├── app/
│   ├── models.py
│   └── service.py
├── static/
│   ├── index.html
│   ├── styles.css
│   └── app.js
├── tests/
│   └── test_service.py
├── data/
├── docs/
│   ├── MANUAL_USUARIO.md
│   ├── ESTRUCTURAS_DATOS.md
│   ├── ANALISIS_RIESGOS_Y_LIMITES.md
│   ├── INDICE_FUNCIONAMIENTO.md
│   ├── API.md
│   ├── ENTREGA_PROYECTO.md
│   └── GUION_VIDEO_5_MIN.md
├── .github/workflows/tests.yml
├── server.py
├── run_tests.py
├── benchmark.py
├── requirements.txt
└── README.md
```

## Porcentaje de IA

La versión entregada como base fue generada aproximadamente en **90 % con asistencia de inteligencia artificial** y en **10 % mediante definición/selección humana del problema, requisitos, validación y ajustes de presentación**. Si el estudiante modifica o amplía el código antes de entregar, debe recalcular este porcentaje de forma honesta.

## Licencia académica

Proyecto preparado con fines educativos. Puede adaptarse para la asignatura indicando autores, curso y universidad.
