# Contenido y SEO

## Tipos de página

El directorio necesita más que fichas individuales.

### Ficha de negocio

Ataca búsquedas de marca e intención concreta:

```text
Es Pont Sóller
opiniones Es Pont
teléfono Es Pont Sóller
```

Incluye datos, descripción, reseñas resumidas, imágenes y contacto.

### Página de localidad

Agrupa negocios y ataca búsquedas genéricas locales:

```text
dónde comer en Sóller
restaurantes en Sóller
restaurantes baratos en Sóller
```

Debe combinar:

- Introducción editorial estable.
- Listado dinámico de restaurantes publicados.
- Resumen y enlace a cada ficha.
- Filtros o bloques por cocina, zona o valoración.
- Preguntas frecuentes.
- Datos estructurados y mapa cuando proceda.

### Página regional

Agrupa localidades, no cientos de fichas sin jerarquía:

```text
Mallorca
├── Sóller
├── Palma
└── Alcúdia
```

## Automatización recomendada

1. Detectar ciudades con un mínimo de negocios publicados.
2. Crear una página de localidad como borrador.
3. Generar una introducción específica una sola vez.
4. Construir el listado de negocios dinámicamente.
5. Actualizar el listado sin volver a llamar a OpenAI.
6. Enlazar fichas hacia su localidad y localidad hacia fichas.
7. Publicar automáticamente solo después de validar varias muestras.

No se debe crear una página geográfica pobre con uno o dos negocios. Un umbral inicial razonable es cinco fichas publicadas.

## Estructura objetivo

```text
País
└── Región o isla
    └── Ciudad
        ├── Página “Dónde comer en…”
        ├── Categoría de cocina
        ├── Distrito o barrio
        └── Fichas de restaurantes
```

## Datos estructurados

Las fichas deberían emitir Schema.org `Restaurant` o `LocalBusiness` con:

- Nombre.
- Dirección postal estructurada.
- Coordenadas.
- Teléfono y web.
- Valoración cuando su uso cumpla las políticas aplicables.
- Imágenes.
- Tipo de cocina.

## Medición

Search Console debe revisarse por:

- Consultas.
- Páginas.
- Impresiones.
- Clics y CTR.
- Posición media.
- Cobertura geográfica.

Una posición media global oculta oportunidades. Las consultas de marca con pocas impresiones pueden conseguir clics antes que términos amplios como `comer bien`.

## Ciclo de mejora

```text
Publicar
→ esperar indexación
→ observar consultas y páginas
→ mejorar títulos, enlazado y páginas geográficas
→ medir durante 4–8 semanas
```

El objetivo no es producir el máximo número de textos, sino construir una red coherente de páginas útiles y conectadas.
