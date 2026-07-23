# Preparación de la migración del CPT

Fecha: 23 de julio de 2026.

## Objetivo

Preparar el traslado del registro del tipo de contenido `restaurante` desde el
tema hacia `mydirectorytool-core` sin activar aún el plugin ni alterar las URLs.

## Cambios publicados

- Tema `mydirectorytool-wp-theme`, commit `e12c0ce`:
  fallback que evita registrar el CPT cuando ya existe.
- Plugin `mydirectorytool-wp-plugin`, commit `6a087af`:
  registro compatible del CPT en prioridad 5 y regeneración de reglas en los
  hooks de activación y desactivación.

## Estado comprobado

- Plugin `mydirectorytool-core`: inactivo.
- Tema activo: `dondecomerbien-theme`.
- Restaurantes publicados: 248.
- Rewrite del CPT: `restaurantes`.
- `show_in_rest`: activo.
- Archivo público: HTTP 200.
- Ficha pública de muestra: HTTP 200.
- Endpoint REST: HTTP 200.
- Sintaxis PHP: correcta en todos los archivos modificados.

## Decisión

No se activa el plugin en este hito. La siguiente operación será crear un backup
inmediatamente anterior, activar el plugin de forma controlada y repetir todas
las comprobaciones. El fallback del tema se conservará durante la transición.
