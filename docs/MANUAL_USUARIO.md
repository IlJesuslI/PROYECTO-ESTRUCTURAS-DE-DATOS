# Manual de usuario — FoodQueue v4.1

## 1. Presentación
FoodQueue es una aplicación local para administrar el menú y los pedidos de un restaurante. Permite registrar productos, recibir pedidos de prioridad **Normal** o **Alta**, preparar pedidos según turnos, cancelar pedidos pendientes y consultar el historial de pedidos preparados. La versión 4.1 utiliza archivos **JSON/JSONL**, sin SQLite.

## 2. Requisitos e inicio
- Python 3.10 o superior y un navegador web actualizado.
- Abrir la carpeta raíz del proyecto, donde está `server.py`.
- En Windows, abrir PowerShell y ejecutar:

```powershell
py server.py
```

- Abrir `http://127.0.0.1:8000` en el navegador.
- Mantener abierta la terminal mientras se utiliza el sistema. Para detenerlo, presionar `Ctrl+C`.
- Para ejecutar las pruebas del proyecto: `py run_tests.py`.

> Si una instalación anterior conserva únicamente una base `state.sqlite3`, la versión JSONL no la migra automáticamente. Conservar una copia y exportar los datos antes de reemplazarlos.

## 3. Pantalla principal
La interfaz tiene tres secciones: **Pedidos**, **Menú** e **Historial**. En la parte superior aparecen indicadores de productos activos, pedidos por preparar, pedidos preparados y pedidos de prioridad alta.

## 4. Menú: agregar, editar y desactivar productos
### Agregar un producto
1. Abrir **Menú**.
2. En **Agregar producto**, escribir el nombre y el precio en pesos colombianos.
3. Pulsar **Guardar producto**.
4. Confirmar que aparece en **Productos activos**.

El nombre es obligatorio, el precio debe ser un entero positivo y no puede existir otro producto **activo** con el mismo nombre (sin distinguir mayúsculas y minúsculas).

### Editar un producto
1. Localizarlo en **Productos activos**.
2. Seleccionar la opción de edición del producto.
3. Modificar nombre o precio y guardar.

Los pedidos ya registrados conservan los nombres y precios capturados cuando fueron creados.

### Desactivar un producto
1. Localizar el producto en **Productos activos**.
2. Seleccionar la opción de desactivación y confirmar cuando corresponda.

Desactivar significa dejar de ofrecer el producto para pedidos nuevos; no equivale a borrar los pedidos anteriores. La API permite cambiar el atributo `active` para reactivar un producto, aunque la interfaz principal se centra en los productos activos.

## 5. Registrar un pedido
1. Abrir **Pedidos** y ubicar **Nuevo pedido**.
2. Escribir el nombre del cliente.
3. Seleccionar **Normal** o **Alta**.
4. Elegir uno o varios productos activos y sus cantidades.
5. Revisar el total y pulsar **Crear pedido**.
6. Comprobar que el pedido aparece en la cola de preparación.

La prioridad Alta tiene atención preferente, pero el sistema intercala un pedido Normal después de hasta tres Altos consecutivos cuando hay Normales esperando. Dentro de cada prioridad se respeta el orden de llegada.

## 6. Consultar, preparar y cancelar pedidos
- **Cola de preparación:** muestra los próximos pedidos en el orden efectivo de atención. La vista puede limitarse a los primeros 60 registros.
- **Preparar siguiente:** pulsar el botón correspondiente; el sistema elige el siguiente pedido elegible, lo marca como preparado y lo agrega al historial.
- **Cancelar:** utilizar la opción de cancelación del pedido pendiente. Un pedido preparado no se puede cancelar mediante esa función.

No se permite seleccionar arbitrariamente qué pedido preparar con el botón **Preparar siguiente**: se aplica la política de prioridades del programa.

## 7. Historial de preparados
1. Abrir **Historial**.
2. Consultar los pedidos preparados, mostrados del más reciente al más antiguo.
3. Si hay más registros, pulsar **Ver más pedidos**.
4. Para eliminar un registro, pulsar **Borrar último**.

**Regla esencial:** solo puede eliminarse el **último pedido preparado**. No existe borrado individual de registros antiguos ni opción para borrar todo el historial. Al borrar el último, el anterior pasa a ser el nuevo último.

## 8. Almacenamiento y copias de seguridad
- `data/state.json`: archivo de estado inicial o heredado, cuando existe.
- `data/state.jsonl`: registro incremental de cambios (un evento JSON por línea).
- Para respaldar los datos, detener el servidor y copiar la carpeta `data/` completa.
- No ejecutar dos servidores simultáneamente sobre los mismos archivos de datos.
- Los archivos de datos están excluidos del control de versiones del proyecto.

## 9. Problemas habituales
| Situación | Qué revisar |
|---|---|
| El navegador no abre FoodQueue | Verificar que `py server.py` siga ejecutándose y abrir el puerto 8000. |
| No se puede agregar un producto | Comprobar nombre, precio y posibles nombres activos duplicados. |
| Un producto no aparece al crear un pedido | Verificar que esté activo. |
| No se puede preparar un pedido | Comprobar que existan pedidos pendientes. |
| No se puede borrar historial | Debe existir al menos un pedido preparado. |
| Aparece un error sobre SQLite anterior | Respaldar los datos antiguos; no existe migración automática. |

## 10. Alcance
FoodQueue está diseñado para demostración académica y uso local. No dispone de autenticación ni de una base transaccional multiusuario; no debe publicarse directamente en internet.
