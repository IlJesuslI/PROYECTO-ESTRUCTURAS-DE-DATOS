# Entrega del proyecto — FoodQueue

## Nombre
**FoodQueue — Sistema de pedidos de restaurante con estructuras lineales**

## Objetivo
Desarrollar una aplicación intuitiva para administrar productos y pedidos de un restaurante, integrando estructuras lineales con un propósito observable por el usuario.

## Tecnologías
- Python 3.10+ para servidor, lógica, validaciones y persistencia.
- JavaScript para interacción en el navegador.
- HTML/CSS para interfaz.
- Biblioteca estándar de Python: `list`, `collections.deque`, `heapq`, `http.server`, `json`, `threading`.

## Estructuras implementadas
1. Arreglo dinámico (`list`) → menú.
2. Cola (`deque`) → pedidos normales.
3. Cola con prioridad (`heapq`) → pedidos altos/urgentes.
4. Pila (`list`) → historial y deshacer.

## Entregables incluidos
- Código fuente comentado.
- Interfaz web.
- Manual de usuario.
- Documento de estructuras de datos.
- Índice de funcionamiento.
- Análisis de riesgos y límites.
- API documentada.
- Guion de video de máximo 5 minutos.
- 10 pruebas unitarias.
- Benchmark reproducible.
- Workflow de GitHub Actions.

## IA
La versión base suministrada fue desarrollada aproximadamente en **90 % con asistencia de IA**. El estudiante debe ajustar este porcentaje si realiza cambios sustanciales antes de la entrega.

## Comandos

```bash
python server.py
python run_tests.py
python benchmark.py 1000
```
