# Activación de MyDirectoryTool Core

Fecha: 23 de julio de 2026.

## Backup previo

Ruta:

`/home/guillem/backups/dondecomerbien/2026-07-23_pre_plugin_activation/`

Contenido:

- `wordpress.sql`
- `dondecomerbien-theme.tar.gz`
- `mydirectorytool-core.tar.gz`
- `SHA256SUMS`

El volcado SQL terminó con su marcador de finalización. Las firmas SHA-256 y
los dos archivos comprimidos fueron verificados.

## Resultado de la activación

- Plugin activo: `mydirectorytool-core/mydirectorytool-core.php`.
- Restaurantes publicados antes: 248.
- Restaurantes publicados después: 248.
- Tema activo: `dondecomerbien-theme`.
- Callback del plugin: prioridad 5.
- Fallback del tema: prioridad 10.
- Slug del CPT: `restaurantes`.
- Archivo del CPT: activo.
- REST del CPT: activo con la ruta por defecto.

## Pruebas públicas

- Portada: HTTP 200.
- Archivo `/restaurantes/`: HTTP 200.
- Ficha existente de muestra: HTTP 200.
- `/wp-json/wp/v2/restaurante?per_page=1`: HTTP 200.
- Logs de la ventana de activación: sin errores PHP.

## Rollback disponible

Si aparece una regresión:

1. Desactivar `mydirectorytool-core`.
2. El fallback del tema volverá a registrar el CPT.
3. Verificar o regenerar las reglas de enlaces permanentes.
4. Restaurar el SQL y los archivos desde el backup previo solo si fuera
   necesario.
