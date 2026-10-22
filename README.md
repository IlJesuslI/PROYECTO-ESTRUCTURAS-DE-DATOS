# FoodQueue

Nuestro sistema consiste en una aplicación web local que permite gestionar las funciones básicas de un restaurante, como administrar el menú y registrar pedidos con diferentes productos, cantidades y prioridades. Emplea estructuras de datos como **arreglos dinámicos, colas FIFO, colas con prioridad y pilas**. Además, evita que los pedidos normales sean desatendidos frente a los prioritarios, permite consultar el historial y deshacer el último pedido preparado.
- Interfaz hecha en JavaScript, HTML y CSS.
- Lógica y procesamiento con Python.

## Requisitos

- **Python:** versión 3.10 o superior.
- **Navegador web:** uno moderno compatible con HTML, CSS y JavaScript.
- **Dependencias:** no requiere instalar bibliotecas externas de Python, ya que utiliza módulos de la biblioteca estándar.
- **Almacenamiento:** permisos de lectura y escritura en el directorio del proyecto para guardar los datos en formato JSON.

## Pruebas automatizadas

FoodQueue incluye pruebas automatizadas para verificar el funcionamiento de las principales operaciones del sistema, como la gestión de pedidos, el orden de atención según las prioridades, la prevención de la inanición de pedidos normales, el historial de pedidos preparados, la opción de deshacer y la persistencia de los datos.

Para ejecutar las pruebas, abre una terminal en la carpeta raíz del proyecto y ejecuta:

```bash
py -m unittest discover -s tests -v
```

Al finalizar, la terminal mostrará si las pruebas se ejecutaron correctamente o si se encontraron errores.

## Benchmark de rendimiento

El proyecto incluye `benchmark.py`, un script que permite medir el tiempo de ejecución de la creación de pedidos, incluyendo el costo de guardar los datos en el archivo JSON. También informa el tiempo promedio por pedido y el tamaño del archivo generado.

Para ejecutar el benchmark con diferentes cantidades de pedidos, utiliza los siguientes comandos desde la carpeta raíz:

```bash
py benchmark.py 100
py benchmark.py 500
py benchmark.py 1000
```

El número indicado representa la cantidad de pedidos que se utilizarán en cada medición. Si no se especifica una cantidad, el script utiliza 1000 pedidos por defecto.

**Importante:** las pruebas automatizadas y el benchmark se ejecutan de forma independiente, por lo que no es necesario iniciar el servidor web antes de utilizarlos. El benchmark utiliza un directorio temporal para sus datos, evitando modificar el archivo de persistencia habitual de la aplicación.

Los resultados pueden variar según las características del equipo y las condiciones de ejecución. Por ello las mediciones sirven como referencia para observar cómo cambia el rendimiento al aumentar la cantidad de pedidos, no como una garantía de tiempos específicos.

## Porcentaje de IA

La versión entregada como base fue generada aproximadamente en **90 % con asistencia de inteligencia artificial** y en **10 % mediante definición/selección humana del problema, requisitos, validación y ajustes de presentación**.


## Hecho por:
- Jesus David Muñoz Gomez
- Edwin Mauricio Cifuentes Monterrey
- Jacobo Atahualpa Manrique Monroy
