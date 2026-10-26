# API HTTP — FoodQueue v3.0

Base: `http://127.0.0.1:8000`. Se emplea JSON UTF-8. Respuesta normal:

```json
{"ok": true, "data": {}}
```

Errores:

```json
{"ok": false, "error": "Descripción"}
```

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/status` | Contadores del sistema |
| GET | `/api/products` | Productos activos |
| GET | `/api/products?all=1` | Todos los productos (incluidos inactivos) |
| POST | `/api/products` | Crear `{ "name": "...", "price_cop": 15000 }` |
| PUT | `/api/products/{uuid}` | Editar `{ "name": "...", "price_cop": 18000 }` |
| DELETE | `/api/products/{uuid}` | Desactivar producto (borrado lógico) |
| POST | `/api/orders` | Crear pedido con prioridad `0` o `1` |
| GET | `/api/orders/pending?limit=60` | Primeros 1–200 pedidos en orden de atención |
| POST | `/api/orders/process-next` | Preparar el siguiente |
| POST | `/api/orders/{uuid}/cancel` | Cancelar pendiente |
| GET | `/api/history?limit=30&offset=0` | Consultar histórico paginado (limit 1–200) |
| DELETE | `/api/history/{uuid}` | **Borrar definitivamente** un preparado |
| DELETE | `/api/history` | **Borrar todos** los preparados |

**El endpoint `POST /api/history/undo` fue eliminado.** Clientes viejos recibirán HTTP 404.

## Registrar un pedido

```http
POST /api/orders
Content-Type: application/json

{
  "customer": "Camila",
  "priority": 1,
  "items": [
    {"product_id": "UUID-DE-PRODUCTO", "quantity": 2}
  ]
}
```

`priority=0` equivale a normal, `priority=1` a alta. Cualquier otro valor (incluido el antiguo `2`) genera HTTP 400.

## Estado

```json
{
  "products_active": 4,
  "orders_pending": 12,
  "orders_prepared": 8,
  "orders_cancelled": 1,
  "normal_queue_size": 8,
  "priority_queue_size": 4,
  "stack_size": 8
}
```

`stack_size` indica preparados **vivos**, no entradas obsoletas del buffer interno tras borrar. Los números anteriores son solo ejemplos.

## Códigos de respuesta

- `200`: operación correcta; `201`: pedido o producto creado.
- `400`: validación fallida, JSON/consulta inválidos.
- `404`: recurso ausente o sin pendientes para procesar.
- `409`: estado del pedido incompatible o nombre activo repetido.
- `500`: error inesperado.

**Seguridad:** esta API no implementa autenticación. Úsese solo en `127.0.0.1` para fines académicos.
