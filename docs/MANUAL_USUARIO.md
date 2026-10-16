# Manual de usuario — FoodQueue

## 1. Requisitos

- Windows, macOS o Linux.
- Python 3.10 o superior.
- Navegador moderno: Chrome, Edge, Firefox o Safari.

## 2. Iniciar el sistema

1. Abrir una terminal dentro de la carpeta `FoodQueue`.
2. Ejecutar:

   ```bash
   python server.py
   ```

3. Abrir `http://127.0.0.1:8000` en el navegador.
4. Para cerrar, volver a la terminal y presionar `Ctrl+C`.

## 3. Pantalla principal

En la parte superior se observan cuatro indicadores:
- Productos activos.
- Pedidos pendientes.
- Pedidos preparados.
- Pedidos actualmente en la cola con prioridad.

Hay cuatro pestañas: **Pedidos, Menú, Historial y Estructuras**.

## 4. Crear productos

1. Entrar en **Menú**.
2. Escribir nombre.
3. Escribir precio en pesos colombianos sin separadores, por ejemplo `18000`.
4. Presionar **Guardar producto**.

Si un producto deja de venderse, usar **Desactivar**. No se elimina de pedidos antiguos.

## 5. Registrar un pedido

1. Entrar en **Pedidos**.
2. Escribir el nombre del cliente.
3. Elegir prioridad:
   - Normal.
   - Alta.
   - Urgente.
4. En el listado de productos, indicar cantidades mayores a 0.
5. Verificar el total estimado.
6. Presionar **Agregar pedido a la cola**.

## 6. Procesar pedidos

Presionar **Preparar siguiente**. El sistema selecciona automáticamente el pedido correcto según la prioridad y el orden de llegada.

La política es: máximo tres pedidos prioritarios seguidos cuando también existen pedidos normales esperando.

## 7. Cancelar

En **Pedidos pendientes**, presionar **Cancelar**. Solo funciona antes de que el pedido sea preparado.

## 8. Deshacer el último preparado

1. Entrar en **Historial**.
2. Presionar **Deshacer último**.
3. El pedido preparado más reciente regresa a pendientes y se reubica según su prioridad.

## 9. Datos persistentes

El estado se guarda en `data/state.json`. Al cerrar y volver a abrir el programa, menú y pedidos se recuperan automáticamente.

Para reiniciar el proyecto desde cero, con el servidor apagado, eliminar `data/state.json`. Al siguiente inicio se generará nuevamente el menú de demostración.

## 10. Mensajes de error comunes

- **“El pedido debe contener al menos un producto”**: seleccione una cantidad mayor a 0.
- **“Ya existe un producto activo…”**: cambie el nombre o desactive el producto anterior.
- **“No hay pedidos pendientes…”**: cree un pedido antes de preparar.
- **“Uno de los productos no existe o ya no está activo”**: recargue la interfaz y seleccione un producto vigente.
