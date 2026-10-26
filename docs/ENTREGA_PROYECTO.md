# Entrega académica — FoodQueue v4

**Lenguajes:** Python (backend) y JavaScript/HTML/CSS (frontend). **Persistencia:** archivos JSON + JSONL; sin SQL ni paquetes externos.

**Estructuras:** arreglo dinámico del menú, dos colas FIFO por arreglos (con prioridad Alta/Normal) y pila de historial. Se cumplen al menos tres estructuras lineales. El diccionario por ID es un índice auxiliar.

**Complejidad:** insertar en cola O(1) amortizado; extraer O(1) amortizado; selección de prioridad O(1); cancelar por ID O(1) esperado; historial O(1) amortizado para apilar y borrar individual, O(h) para vaciar. Arranque O(n log n + e). Ver `COMPLEJIDAD_ALGORITMICA.md`.

**Documentos:** README, manual, API, complejidad, estructuras, análisis de riesgos, índice de funcionamiento y guion para video. **Declaración IA:** estimar y declarar el porcentaje real de código desarrollado con herramientas de IA según los aportes del equipo; no asignar un porcentaje ficticio.

**Pruebas:** `py run_tests.py` y `py benchmark.py 100000`. **Repositorio:** publicar mediante Git y Pull Request. **Video:** máximo 5 minutos.
