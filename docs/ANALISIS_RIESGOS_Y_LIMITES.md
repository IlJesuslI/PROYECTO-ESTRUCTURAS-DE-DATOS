# Riesgos y límites — FoodQueue v4

- **Volumen de datos:** la creación y atención de un pedido no reescribe todo el historial, porque el guardado es incremental JSONL. El diario crece y hace más lento el reinicio.
- **Memoria:** todos los pedidos se cargan en RAM; consumo O(n). Para millones de pedidos se requiere carga parcial y archivo compactado.
- **Durabilidad:** el JSONL se escribe con buffer normal, sin transacciones ACID ni `fsync` por operación. Un apagón puede perder las últimas escrituras. Una última línea truncada se ignora; corrupción intermedia puede impedir iniciar.
- **Concurrencia:** `RLock` protege hilos del mismo servidor, no dos procesos. No ejecutar servidores paralelos con los mismos archivos.
- **Fallo de disco:** una operación cambia memoria antes de escribir el evento; si el disco falla, puede quedar estado desincronizado. Reinicia tras restaurar una copia válida.
- **Cancelaciones:** se saltan al avanzar el cursor; si hay miles seguidas, una extracción puntual puede tardar O(c), aunque amortizado sea O(1).
- **Historial:** solo se borra el último preparado (LIFO); registros heredados pueden contener marcas obsoletas. Paginación por offset tiene costo lineal en desplazamiento.
- **Migración:** si tu versión anterior usaba un archivo SQL, no hay importación automática. Haz respaldo y exporta a JSON antes de cambiar.
- **Seguridad:** aplicación local sin cuentas; no exponer el puerto a internet.
