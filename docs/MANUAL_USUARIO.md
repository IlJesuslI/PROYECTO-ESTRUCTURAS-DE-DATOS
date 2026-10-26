# Manual de usuario — FoodQueue v3.0

## 1. Preparación

1. Instale Python 3.10+.
2. Extraiga el ZIP de FoodQueue.
3. Abra la carpeta `FoodQueue` en Visual Studio Code.
4. Abra **Terminal → New Terminal** y ejecute:

   ```powershell
   py run_tests.py
   py server.py
   ```

5. Abra **http://127.0.0.1:8000** en el navegador. Para detener el servidor, `Ctrl + C`.

No es necesario ejecutar `pip install`. Si Python en su equipo se invoca con `python`, úselo en lugar de `py`.

## 2. Pantalla principal

La navegación lateral permite acceder a **Pedidos**, **Menú** e **Historial**. La sección «Estructuras» ya no aparece en la interfaz, pero su explicación académica se encuentra en el directorio `docs`.

En la cabecera figuran cuatro estadísticas: productos activos, pendientes, preparados y pedidos de prioridad alta que permanecen en espera.

## 3. Registrar pedidos

1. Abra **Pedidos**.
2. Introduzca el nombre del cliente (máximo 80 caracteres).
3. Elija una de las únicas dos prioridades: **Normal** o **Alta**.
4. Seleccione cantidades de los productos disponibles (0 significa no incluir).
5. Revise el total calculado en COP.
6. Seleccione **Crear pedido**.

El sistema verifica nuevamente los datos en el servidor para impedir cantidades decimales o negativas, productos inactivos y pedidos vacíos. Los precios se calculan como enteros COP y quedan fijados en el pedido aunque posteriormente cambie el menú.

## 4. Preparar el siguiente pedido

En el panel **Cola de preparación**, haga clic en **Preparar siguiente**. El algoritmo decide por los dos arreglos independientes, sin buscar dentro de toda la cola:

- Si hay pedidos altos, se atienden primero (FIFO entre ellos).
- Si también hay normales, tras **3 pedidos altos consecutivos** se prepara un normal.
- Los normales se atienden FIFO.

La lista muestra **hasta 60 pedidos** por carga; el contador refleja todos los pendientes. Que solo se muestren 60 no significa que se hayan perdido los demás.

## 5. Cancelar un pedido pendiente

En la tarjeta del pedido, seleccione **Cancelar** y confirme. La cancelación no altera el orden de los demás pedidos. No es posible cancelar un pedido que ya está preparado.

## 6. Administrar el menú

Abra **Menú** para agregar productos nuevos. El nombre debe ser único entre productos activos; el precio es un entero positivo. Un producto puede **editarse** o **desactivarse**. Desactivarlo evita pedidos nuevos con ese producto, pero conserva la información que fue vendida en pedidos anteriores.

## 7. Historial de preparados: BORRAR

- **Borrar** (en una tarjeta): elimina solo ese pedido preparado.
- **Borrar historial** (arriba): elimina todos los pedidos preparados tras confirmar.
- **Ver más pedidos**: carga otra página de 30 registros, si existen.

**ATENCIÓN:** el borrado es permanente en la base de datos. Se eliminó la función **Deshacer último**: borrar un preparado **no lo devuelve a pendientes**. Si el pedido necesita prepararse de nuevo, registre uno nuevo.

## 8. Base de datos y copia de seguridad

Los archivos persistentes están en `data/` (normalmente `state.sqlite3`). Para hacer una copia manual, **detenga primero el servidor**, espere a que termine, y copie la carpeta completa, incluidos archivos temporales `-wal` y `-shm` cuando estén presentes. Nunca incluya `data/` real en GitHub. Para respaldo consistente con servidor en uso, emplee la API SQLite Backup (no implementada en esta versión).

### Cambio desde una versión anterior

La primera ejecución actualiza automáticamente la antigua prioridad `2` («Urgente») a `1` («Alta»). La prioridad `0` permanece como Normal. Si aún existe solo `state.json`, se importa a SQLite conservando los pedidos. El archivo JSON no se borra automáticamente.

## 9. Verificar rendimiento y funcionamiento

```powershell
py run_tests.py
py benchmark.py 10000
py benchmark.py 100000
```

El benchmark crea su propia base **temporal**, no registra 100.000 pedidos ficticios dentro de la base real del restaurante. Sus tiempos varían según el equipo.

## 10. Solución de errores frecuentes

- **`py` no se reconoce:** instale Python o use `python` si ya está en su PATH.
- **Puerto 8000 ocupado:** detenga el servidor anterior o ejecute `py server.py --port 8001`.
- **El navegador no carga:** compruebe la dirección local y el estado del proceso.
- **`database is locked`:** no ejecute múltiples copias del servidor sobre el mismo archivo SQLite; cierre los procesos duplicados.
- **Los cambios no aparecen tras reemplazar archivos:** cierre el servidor anterior y vuelva a iniciarlo; actualice el navegador con Ctrl+F5.
- **Los datos no aparecen después de actualizar:** compruebe que copió su carpeta `data` antigua a la ubicación correcta. Restaure la copia de seguridad si fuera necesario.
- **Error por prioridad `2`:** el formulario nuevo usa únicamente `0` o `1`; actualice los clientes antiguos de la API.
