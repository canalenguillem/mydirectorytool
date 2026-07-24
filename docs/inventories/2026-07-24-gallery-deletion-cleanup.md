# Limpieza de galerías al eliminar adjuntos

Fecha: 24 de julio de 2026.

## Incidencia

En SELVA WOK se eliminó desde la biblioteca de WordPress una fotografía no
adecuada. El archivo desapareció, pero su URL continuó dentro del campo ACF
`place_gallery`, por lo que la ficha pública mostraba una imagen rota.

Post:

```text
3720
```

URL eliminada del campo:

```text
https://dondecomerbien.com/wp-content/uploads/2026/07/ChIJJUOGWgBtRw0RAM-QLMSu2oE_5.jpeg
```

## Corrección de la ficha

- Se comprobó individualmente el estado HTTP de las nueve URLs.
- Solo la imagen `_5.jpeg` devolvía 404.
- Se retiró únicamente esa URL de `place_gallery`.
- La ficha conserva ocho imágenes válidas.
- La página renderiza cuatro parejas y responde HTTP 200.

## Prevención

Plugin `MyDirectoryTool Core` actualizado a 0.6.0:

- registra el hook `delete_attachment`;
- obtiene la URL antes de eliminar definitivamente el adjunto;
- localiza fichas cuyo `place_gallery` contiene esa URL;
- elimina la coincidencia exacta;
- conserva el resto de la galería;
- activa también el hook de sincronización ACF que estaba implementado pero no
  se registraba durante el arranque.

Validaciones:

- PHP sin errores de sintaxis;
- hook de borrado registrado con prioridad 10;
- hook de ACF registrado con prioridad 20;
- SELVA WOK sin referencias a la URL eliminada.

