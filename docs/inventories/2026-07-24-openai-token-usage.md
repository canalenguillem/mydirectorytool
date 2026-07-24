# Registro de uso de tokens de OpenAI

Fecha de implantación: 24 de julio de 2026.

## Objetivo

MyDirectoryTool registra de forma persistente el consumo de OpenAI para poder
medir el coste real de cada automatización antes de aplicar optimizaciones o
límites de presupuesto.

## Datos registrados

Cada respuesta satisfactoria de OpenAI guarda:

- fecha y hora;
- operación;
- modelo devuelto por OpenAI;
- `place_id`, cuando la llamada pertenece a un comercio;
- tokens de entrada;
- tokens de salida;
- tokens totales;
- tokens de entrada en caché, cuando OpenAI informa de ellos;
- identificador de la respuesta.

Las operaciones iniciales son:

- `article_generation`;
- `excerpt_generation`;
- `food_type_classification`.

No se almacenan prompts, respuestas, claves API ni reseñas en esta tabla.

## Persistencia y consulta

La tabla `openai_usage` se crea de forma idempotente al iniciar el backend. Los
índices por fecha y comercio permiten generar resúmenes y futuras auditorías.

El endpoint autenticado `GET /usage/summary?days=30` devuelve el total del
periodo y el desglose por operación y modelo. El panel consulta este resumen
cada diez segundos y presenta peticiones y tokens de entrada, salida y total.

## Alcance histórico

El contador empieza en el despliegue de esta funcionalidad. No reconstruye el
consumo anterior porque el proyecto no conservaba los metadatos de uso de cada
respuesta. El panel oficial de OpenAI continúa siendo la fuente para el
histórico previo.

## Evolución prevista

- migrar la misma tabla a PostgreSQL;
- añadir periodos configurables;
- calcular costes usando una tabla versionada de precios;
- establecer alertas y presupuestos diarios por directorio;
- separar el consumo por instalación, cliente y tipo de directorio.
