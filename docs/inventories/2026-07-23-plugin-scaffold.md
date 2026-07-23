# Esqueleto inicial del plugin

Fecha: 23 de julio de 2026.

## Ubicación

```text
/home/guillem/docker/wp_dondecomerbien/wp_data/wp-content/plugins/mydirectorytool-core/
```

## Estado

```text
nombre: MyDirectoryTool Core
versión: 0.1.0
detectado por WordPress: sí
activo: no
efectos funcionales: ninguno
commit local: 3de04e8
rama: main
```

El plugin no registra todavía CPT, taxonomías, endpoints ni Schema.org. Esta
decisión permite versionar y revisar el esqueleto antes de cambiar la estructura
del sitio.

## Archivos

```text
mydirectorytool-core.php
includes/class-plugin.php
includes/class-post-types.php
includes/class-taxonomies.php
includes/class-acf-sync.php
includes/class-schema.php
includes/class-capabilities.php
uninstall.php
README.md
readme.txt
.gitignore
```

## Validación

- Todos los PHP responden `No syntax errors detected`.
- Validación ejecutada dentro de `wp_dondecomerbien_site` con PHP 8.2.
- WordPress mantiene el tema `dondecomerbien-theme`.
- WordPress mantiene 248 posts `restaurante` publicados.
- La desinstalación no borra contenido ni configuración.

## Git

```text
origin: git@github.com:canalenguillem/mydirectorytool-wp-plugin.git
commit: 3de04e8 Initial plugin scaffold
```

El remoto no existía al finalizar esta sesión. Debe crearse vacío en GitHub con
el nombre `canalenguillem/mydirectorytool-wp-plugin`; después se ejecutará:

```bash
git push -u origin main
```

No activar el plugin hasta completar el fallback temporal del CPT en el tema y
las pruebas descritas en el runbook.
