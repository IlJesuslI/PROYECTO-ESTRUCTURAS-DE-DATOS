# Índice de funcionamiento — FoodQueue v3.0

## Flujo de uso

1. **Iniciar:** `py server.py` y abrir `http://127.0.0.1:8000`.
2. **Conocer el resumen:** leer productos activos, pedidos pendientes, preparados y altos.
3. **Administrar el menú:** registrar, editar, consultar o desactivar productos.
4. **Crear pedido:** cliente → prioridad **Normal/Alta** → productos/cantidades → confirmar.
5. **Encolar:** el objeto `Order` entra por `append()` al arreglo de su prioridad, sin buscar posiciones.
6. **Atender:** elegir arreglo por contadores; leer `items[head]`; avanzar `head`.
7. **Garantizar equidad:** máximo tres altas consecutivas mientras existan normales.
8. **Preparar:** cambiar a estado `prepared`, registrar fecha, apilar ID y guardar en SQLite.
9. **Cancelar pendiente:** cambio de estado por ID; una marca obsoleta se ignora cuando llega al frente.
10. **Consultar pendientes:** solo se devuelven las primeras 60 posiciones combinadas conforme a la regla de turnos.
11. **Historial:** lectura por páginas de 30 preparados, del más reciente al más antiguo.
12. **Borrar:** eliminar un preparado o todos los preparados; ya no existe **Deshacer**.
13. **Persistencia:** cada operación escribe la fila afectada en SQLite, sin volver a serializar el archivo completo.
14. **Reinicio:** se reconstruyen las colas con `queue_seq` y el orden de preparación con `stack_seq`.
15. **Pruebas:** `py run_tests.py` y `py benchmark.py 100000`.

## Diagrama de datos

```text
         PRODUCTOS (list dinámica)
                     │
               CREAR PEDIDO
                     │
            ¿priority == 1?
                 /       \
               Sí         No
               │           │
   ARREGLO ALTA          ARREGLO NORMAL
    [A1,A2,...]           [N1,N2,...]
       headA                headN
          \                /
           \              /
     SELECTOR DE TURNO O(1)
     alta ×3 → normal ×1
                 │
        PREPARAR Y GUARDAR
                 │
     PILA prepared_stack.append()
                 │
      HISTORIAL (SQLite paginado)
                 │
         BORRAR (sin deshacer)
```

## Regla de persistencia

- Inicio sin archivo SQLite: crea base inicial o importa `data/state.json` si existe.
- Inicio con SQLite anterior: actualiza prioridad `2 → 1` en todas las filas afectadas.
- Eliminar del historial borra filas preparadas; **no** elimina pendientes ni cancelados.
