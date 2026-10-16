# API HTTP — FoodQueue

Base local: `http://127.0.0.1:8000`

| Método | Ruta | Función |
|---|---|---|
| GET | `/api/status` | Métricas |
| GET | `/api/products` | Productos activos |
| POST | `/api/products` | Crear producto |
| PUT | `/api/products/{id}` | Modificar producto |
| DELETE | `/api/products/{id}` | Desactivar producto |
| GET | `/api/orders/pending` | Pedidos pendientes |
| POST | `/api/orders` | Crear pedido |
| POST | `/api/orders/process-next` | Preparar siguiente |
| POST | `/api/orders/{id}/cancel` | Cancelar pendiente |
| GET | `/api/history?limit=50` | Historial LIFO |
| POST | `/api/history/undo` | Deshacer último preparado |
