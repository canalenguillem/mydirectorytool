# Hoja de ruta

## Fase 0: estabilizar el directorio gastronómico

Estado: en curso.

- Completar y observar la cola actual.
- Validar publicaciones en varias ciudades.
- Revisar errores, duplicados, títulos, imágenes y ACF.
- Añadir ciudades en lotes moderados.
- Mantener copias de seguridad.
- Confirmar crecimiento de indexación e impresiones.

No se debe hacer una gran refactorización mientras una publicación masiva esté activa.

## Fase 1: calidad y robustez

- Homogeneizar respuestas y códigos HTTP.
- Añadir timeouts y reintentos específicos a todas las integraciones.
- Evitar duplicados de lugares, reseñas e imágenes mediante restricciones.
- Introducir migraciones de base de datos.
- Añadir pruebas unitarias y de integración con mocks.
- Añadir logs estructurados y métricas de costes.
- Crear proceso seguro de enriquecimiento histórico por lotes.

Resultado: un pipeline fiable que puede operar durante días sin supervisión constante.

## Fase 2: estructura pública del directorio

- Crear taxonomía o contenido de localidad en WordPress.
- Generar páginas de ciudad como borradores.
- Listar restaurantes dinámicamente.
- Crear enlazado bidireccional.
- Añadir Schema.org.
- Generar sitemap geográfico.
- Incorporar páginas regionales cuando haya suficiente cobertura.

Resultado: las fichas dejan de estar aisladas y forman un directorio navegable.

## Fase 3: núcleo multidirectorio

- Crear entidad `directory`.
- Registrar Dónde comer bien como primer proyecto.
- Asociar negocios, plantillas, cola y publicaciones a `directory_id`.
- Separar `business` de su participación en un directorio.
- Configurar destino WordPress por proyecto.
- Configurar mapeo de campos y taxonomías.
- Añadir selector de directorio en el panel.

Resultado: una instalación puede gestionar varios dominios sin duplicar código.

## Fase 4: asistente para nuevos directorios

El alta debe solicitar:

- Nombre, sector e idioma.
- Dominio y credenciales del CMS.
- Tipo de contenido y taxonomías.
- Campos del negocio.
- Plantilla editorial.
- Reglas de títulos.
- Ritmo de publicación.
- Territorio inicial.

El asistente debe crear un proyecto en borrador y ejecutar pruebas de conexión antes de permitir publicaciones.

## Fase 5: enriquecimiento y contacto comercial

- Capturar correo solo desde fuentes autorizadas y registrando procedencia.
- Permitir corrección manual de contacto.
- Registrar fecha de verificación.
- Detectar negocios sin web como posibles oportunidades.
- Crear un CRM ligero separado del contenido editorial.
- Respetar normativa de privacidad y comunicaciones comerciales.

No se debe mezclar automáticamente publicación editorial con campañas de contacto.

## Fase 6: escalabilidad

- PostgreSQL.
- Worker separado con cola dedicada.
- Programación distribuida.
- Almacenamiento de objetos para imágenes.
- Roles y permisos.
- Auditoría.
- Límites y presupuesto por directorio.
- Panel de salud y costes.

## Próximas decisiones

Cuando termine la cola actual, el orden recomendado es:

1. Copia de seguridad y revisión de errores.
2. Enriquecimiento geográfico histórico en lotes pequeños.
3. Páginas de localidad para las ciudades con más fichas.
4. Restricciones de integridad y migraciones.
5. Introducción de `directory` sin cambiar todavía el comportamiento visible.

## Definición de producto a largo plazo

MyDirectoryTool será una plataforma privada para configurar, poblar, publicar y mantener directorios verticales, con conectores de fuentes y CMS reemplazables y automatización supervisada de extremo a extremo.
