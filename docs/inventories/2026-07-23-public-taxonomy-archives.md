# Archivos públicos de taxonomía

Fecha: 23 de julio de 2026.

## Versiones

- Tema `mydirectorytool-wp-theme`: commit `136d1ff`.
- Plugin `mydirectorytool-core`: versión 0.4.1, commit `cd43c57`.

## URLs definitivas

```text
/restaurantes/municipio/{termino}/
/restaurantes/provincia/{termino}/
/restaurantes/tipo-comida/{termino}/
```

Ejemplos verificados:

```text
/restaurantes/municipio/soller/
/restaurantes/provincia/illes-balears/
/restaurantes/tipo-comida/mediterranea/
```

## Tema

Se añadieron:

- `taxonomy.php`, compartida por las tres taxonomías.
- `template-parts/card-restaurante.php`, compartida por el archivo general y
  las taxonomías.
- H1 contextual:
  - `Restaurantes en Sóller`
  - `Restaurantes en Illes Balears`
  - `Restaurantes de cocina Mediterránea`
- Imagen de fallback cuando falta la destacada.
- Municipio y tipo de comida enlazados desde cada tarjeta.
- Paginación accesible.
- Estilos para cabecera, tarjetas, metadatos y paginación.

El archivo general pasó de duplicar el HTML de la tarjeta a reutilizar el mismo
componente.

## Plugin

Las taxonomías quedaron públicas y consultables, con REST activo y rewrites
estables bajo `/restaurantes/`.

WordPress colocaba inicialmente las reglas de adjuntos del CPT antes que las
taxonomías y devolvía 404. La versión 0.4.1 añade reglas específicas en prioridad
alta para la primera página y la paginación.

## Validaciones

- Sintaxis PHP del tema y plugin: correcta.
- CSS: llaves equilibradas.
- Municipio Sóller: HTTP 200 y listado presente.
- Provincia Illes Balears: HTTP 200 y listado presente.
- Tipo Mediterránea: HTTP 200 y listado presente.
- Página 2 de provincia: HTTP 200.
- Página 2 de tipo: HTTP 200.
- Archivo general: HTTP 200.
- Ficha existente: HTTP 200.
- REST de restaurantes: HTTP 200.
- Logs PHP durante el despliegue: sin errores.

## Pendiente

- Mejorar la plantilla individual.
- Añadir migas de pan.
- Definir canonical y metadatos sociales sin duplicados.
- Añadir descripciones editoriales a los términos prioritarios.
- Revisar la presentación móvil en navegador.
