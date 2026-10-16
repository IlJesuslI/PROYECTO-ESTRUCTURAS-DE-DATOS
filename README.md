# FoodQueue

Nuestro sistema consiste en una aplicación web local que permite gestionar las funciones básicas de un restaurante, como administrar el menú y registrar pedidos con diferentes productos, cantidades y prioridades. Emplea estructuras de datos como **arreglos dinámicos, colas FIFO, colas con prioridad y pilas**. Además, evita que los pedidos normales sean desatendidos frente a los prioritarios, permite consultar el historial y deshacer el último pedido preparado.
- Interfaz hecha en JavaScript, HTML y CSS.
- Lógica y procesamiento con Python.

## Estructuras de datos

| Estructura | Implementación Python | Uso | Operación principal |
|---|---|---|---|
| Arreglo dinámico | `list` | Menú de productos | `append` \(O(1)\) |
| Cola | `collections.deque` | Pedidos normales | `append` / `popleft` \(O(1)\) |
| Cola con prioridad | `heapq` | Pedidos alta/urgente | `heappush()` / `heappop()` \(O(log n)\) |
| Pila | `list` | Historial de preparados | `append` / `pop` \(O(1)\) |

En lugar de implementar clases propias para estas estructuras, se utilizaron las implementaciones nativas de Python para aprovechar sus operaciones optimizadas y mantener complejidades temporales constantes \(O(1)\) y logarítmicas \(O(\log n)\), según la operación. Ambas se encuentran entre los órdenes de complejidad más eficientes de la escala Big O, lo que favorece el rendimiento del sistema.

## Ejecutar

Para la ejecución se necesita Python 3.10 o superior y ejecutar en la terminal del sistema el siguiente comando:
```
python server.py
```
Si la ejecución se realiza correctamente, la terminal mostrará la dirección local donde estará disponible la interfaz funcional: _http://127.0.0.1:8000_

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

La versión entregada como base fue generada aproximadamente en **90 % con asistencia de inteligencia artificial** y en **10 % mediante definición/selección humana del problema, requisitos, validación y ajustes de presentación**.

