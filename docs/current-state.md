# Estado actual

## Producto operativo

El proyecto ya funciona como back office de un directorio gastronómico. Está desplegado con Docker y publica fichas de restaurantes en WordPress.

## Funcionalidades terminadas

### Acceso y despliegue

- Login privado para el panel.
- Sesión firmada mediante cookie `HttpOnly`.
- Frontend como único puerto expuesto (`8091`).
- Backend accesible únicamente desde la red interna de Docker.
- Configuración sensible excluida de Git.
- Código versionado en GitHub.

### Descubrimiento y selección

- Búsqueda mediante Google Places.
- Resultados separados de los negocios guardados.
- Guardado individual sin abandonar la pantalla de resultados.
- Indicador visual de resultados ya guardados.
- Una petición de detalles por resultado en lugar de dos.
- Pausa configurable entre peticiones a Google.
- Conservación de resultados básicos si falla un detalle concreto.

### Datos del negocio

- Nombre, dirección, Place ID y valoración.
- Teléfono y web cuando Google los proporciona.
- País y código de país.
- Región, provincia, municipio, ciudad y distrito.
- Código postal.
- Latitud y longitud.
- Estado operativo de Google.
- Campos reservados para correo y procedencia del correo.

Google Places no proporciona correos electrónicos. No hay scraping de webs activo.

### Control de calidad

- Filtro de negocios con datos incompletos.
- Subfiltros por contacto, ubicación, imágenes y tipo de comida.
- Detección de referencias publicadas que han perdido su artículo en WordPress.
- Actualización bajo demanda de contacto y geografía mediante una única consulta
  de detalles a Google.
- Sincronización de los nuevos valores con ACF si la ficha ya está publicada.
- Etiquetas visibles en cada ficha con las carencias concretas.
- El estado se calcula desde los datos actuales y no se persiste de forma
  redundante.
- Auditoría reutilizable y de solo lectura sobre el contenido de WordPress.

### Contenido

- Obtención y almacenamiento de reseñas.
- Generación de artículos Markdown con OpenAI.
- Veinte estructuras deterministas para evitar títulos repetitivos.
- Limpieza de bloques Markdown incorrectos.
- Caché de artículos ya generados.
- Regeneración cuando una referencia antigua apunta a un archivo inexistente.
- Generación de extractos.
- Clasificación básica del tipo de comida.

### Imágenes y WordPress

- Descarga de fotografías de Google Places.
- Selección de imagen destacada.
- Subida de imagen destacada y galería a WordPress.
- Eliminación de la doble subida de imágenes.
- Publicación como tipo de contenido `restaurante`.
- Escritura de campos ACF de contacto, ubicación, cocina y Place ID.
- Registro local del ID y URL del post publicado.

### Cola automática

- Cola persistente en SQLite.
- Un trabajo cada cinco minutos por defecto.
- Inicio con lote de prueba o incorporación de todos los pendientes.
- Pausa y reanudación.
- Máximo de tres intentos.
- Recuperación tras reiniciar Docker.
- Protección frente a dos workers locales simultáneos.
- Estado, tiempo estimado y errores recientes en el panel.

### Cola de reparación

- Cola persistente separada para fichas incompletas.
- Repara únicamente los datos o recursos que falten.
- Una ficha cada cinco minutos y máximo de tres intentos.
- Sincroniza ACF y vuelve a publicar únicamente posts eliminados.
- Pausa, reanudación, errores recientes y reintentos desde el panel.

## Problemas resueltos durante el MVP

- Resultados de búsqueda guardados automáticamente sin consentimiento.
- Pantalla de resultados que desaparecía al guardar uno.
- Títulos repetidos a partir de ejemplos literales del prompt.
- Galerías subidas dos veces.
- Reintentos que podían republicar un negocio ya marcado como publicado.
- Rutas antiguas de artículos incompatibles con el volumen Docker.
- Backend expuesto directamente al host.
- Ausencia de autenticación.

## Limitaciones actuales

- Solo existe un proyecto real y una configuración de WordPress.
- El código contiene conceptos específicos de restaurantes.
- Las credenciales de WordPress viven en variables de entorno globales.
- SQLite no tiene todavía un sistema formal de migraciones.
- Los registros históricos no están enriquecidos con la nueva geografía.
- El correo no se obtiene automáticamente.
- No existen páginas automáticas de ciudad, provincia o categoría.
- No hay sincronización de cambios desde WordPress hacia la base local.
- El contador de publicados del panel refleja el estado local; puede diferir de
  WordPress si un post se elimina directamente en el CMS.
- La API todavía necesita homogeneizar códigos HTTP, timeouts y errores.
- Faltan pruebas automatizadas completas y CI.
- La cola ejecuta tareas largas dentro del proceso del backend; una arquitectura de workers independiente será más robusta al crecer.

## Criterio de éxito del MVP gastronómico

El MVP se considera validado cuando:

- Una muestra de varias ciudades publica sin duplicados.
- Los campos geográficos llegan correctamente a WordPress.
- La cola completa lotes largos sin intervención constante.
- Los artículos mantienen variedad y veracidad razonables.
- Search Console muestra crecimiento de páginas indexadas e impresiones.
- Se pueden identificar y reintentar fallos concretos.
