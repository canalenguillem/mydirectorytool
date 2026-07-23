# Ficha individual y galería intercalada

Fecha: 23 de julio de 2026.

Tema `mydirectorytool-wp-theme`, versión 1.2, commit `7dc7b29`.

## Regla editorial reutilizable

La galería no se presenta como un bloque completo al final:

1. La imagen destacada aparece al principio.
2. `place_gallery` se limpia, valida y divide en parejas.
3. Se inserta una pareja después de cada dos párrafos.
4. Si el artículo tiene menos párrafos que parejas, las imágenes restantes se
   conservan al final.
5. En escritorio se muestran dos columnas.
6. En móvil se muestran en una columna.

Esta regla debe ser configurable por tipo de directorio en el futuro. Por
ejemplo, un directorio de peluquerías podrá conservar parejas, usar imágenes
individuales o cambiar la frecuencia sin modificar el contenido almacenado.

## Rendimiento y accesibilidad

- Se reutiliza `wp_get_attachment_image()` cuando la URL corresponde a un
  adjunto local.
- WordPress genera `srcset` y tamaños responsivos.
- Las imágenes intercaladas usan carga diferida.
- La imagen destacada tiene prioridad de carga.
- Cada foto recibe un texto alternativo basado en el nombre del establecimiento.
- Cada pareja se identifica como un grupo de fotos.

## Datos visibles en la ficha

- Migas de pan.
- Tipo de comida.
- Municipio.
- Provincia.
- Teléfono.
- Web.
- Correo, si existe.
- Código postal, si existe.
- Mapa OpenStreetMap con latitud y longitud.

Los bloques se omiten cuando no existen datos; no se muestran valores inventados
ni contenedores vacíos.

## Validación

Ficha utilizada:

`/restaurantes/lo-mejor-de-burdo-restaurante-y-brunch-segun-quienes-ya-se-han-sentado-a-su-mesa/`

Resultado:

- HTTP 200.
- Cinco parejas de imágenes.
- Parejas insertadas entre los párrafos.
- Migas presentes.
- Contacto presente.
- Mapa presente.
- Enlaces de taxonomía presentes.
- Archivo general: HTTP 200.
- Taxonomía Cala Millor: HTTP 200.
- Errores PHP: ninguno.
