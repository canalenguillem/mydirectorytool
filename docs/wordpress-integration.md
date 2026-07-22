# Arquitectura de WordPress

La integración pública del directorio debe separar los datos, la estructura
funcional y la presentación. Esta separación es una decisión base del proyecto:
un cambio de tema no puede eliminar taxonomías, URLs, datos estructurados ni la
lógica del directorio.

## Reparto de responsabilidades

### MyDirectoryTool

La herramienta privada se encarga de:

- Descubrir, seleccionar y enriquecer negocios.
- Guardar datos normalizados y archivos fuente.
- Generar contenido e imágenes.
- Publicar fichas y actualizar ACF.
- Gestionar la cola, los reintentos y los diferentes destinos WordPress.

No debe controlar el diseño público de cada sitio.

### Plugin propio del directorio

Un plugin pequeño y estable se encargará de:

- Registrar el tipo de contenido `restaurante`.
- Registrar taxonomías como municipio, provincia y tipo de comida.
- Sincronizar ACF con términos cuando corresponda.
- Generar datos estructurados Schema.org (`Restaurant`/`LocalBusiness`).
- Mantener reglas de URLs, archivos y relaciones aunque cambie el tema.

Las taxonomías no deben registrarse únicamente en el tema. Son parte del modelo
del directorio y necesitan sobrevivir a cualquier rediseño.

### Tema hijo

El tema hijo controla únicamente la presentación:

- Plantilla individual de restaurante.
- Archivo general y páginas por taxonomía/localidad.
- Tarjetas reutilizables, listados y filtros.
- Migas de pan y enlaces internos visibles.
- Mapa y botones para llamar o visitar la web.
- Estilos, composición responsive y accesibilidad.
- Etiquetas sociales Open Graph visibles en el HTML, incluida `og:image` a
  partir de la imagen destacada, si no las aporta otro plugin estable.

## Primer conjunto de archivos

```text
plugin del directorio
├── registro del CPT restaurante
├── taxonomía municipio
├── taxonomía provincia
├── taxonomía tipo_de_comida
└── Schema.org

tema hijo
├── single-restaurante.php
├── archive-restaurante.php
├── taxonomy-municipio.php
└── template-parts/card-restaurante.php
```

## Páginas geográficas

Los campos ACF conservan el valor detallado recibido desde la herramienta, pero
municipio, provincia y tipo de comida también deben representarse mediante
taxonomías. Esto proporciona:

- URLs y archivos propios.
- Consultas y filtros nativos de WordPress.
- Enlazado automático entre fichas y territorios.
- Sitemaps y una estructura más comprensible para buscadores.

Ejemplo:

```text
Mallorca
└── Sóller
    ├── Dónde comer en Sóller
    ├── Restaurante A
    └── Restaurante B
```

## Orden de implementación

1. Crear el plugin y registrar taxonomías sin cambiar todavía el diseño.
2. Sincronizar las fichas existentes y comprobar términos/URLs.
3. Crear el tema hijo y la plantilla individual.
4. Añadir archivos por localidad y tarjetas reutilizables.
5. Incorporar Schema.org, enlaces internos, mapas y etiquetas Open Graph.
6. Probar en un entorno de staging antes de activar los cambios en producción.
