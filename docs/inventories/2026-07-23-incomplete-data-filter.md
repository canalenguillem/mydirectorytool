# Auditoría actualizada y filtro de datos incompletos

Fecha: 23 de julio de 2026.

## Reconciliación

El contador del panel muestra 279 registros locales marcados como publicados.
WordPress contiene 272 posts `restaurante` publicados.

La diferencia coincide con el inventario histórico conocido:

```text
279 locales - 8 referencias a posts eliminados + 1 post huérfano = 272
```

Referencias locales cuyo `wp_post_id` ya no existe:

```text
8, 10, 12, 23, 36, 52, 316, 363
```

Post de WordPress sin referencia local publicada:

```text
44
```

No se modificó ningún registro durante la reconciliación. Marcar las ocho
referencias como pendientes podría volver a publicar negocios eliminados
intencionadamente.

## Auditoría de WordPress

| Señal | Resultado |
|---|---:|
| Restaurantes publicados reales | 272 |
| Sin imagen destacada | 0 |
| Sin galería | 23 |
| Sin contacto | 11 |
| Sin ubicación completa | 51 |
| Sin extracto | 0 |
| Títulos de más de 70 caracteres | 68 |
| Contenido de menos de 300 palabras | 0 |
| Fichas con alguna alerta | 118 |
| Términos con una o dos fichas | 94 |

Los diez títulos de la muestra anterior explican la bajada de 78 a 68 títulos
largos.

## Filtro del panel

El backend calcula el estado de integridad al listar los negocios, sin guardar
datos derivados nuevos en SQLite.

Categorías:

- contacto: falta teléfono, web y correo;
- ubicación: falta municipio/ciudad, coordenadas, código postal o código de
  país;
- imágenes: no existen imágenes locales registradas;
- tipo de comida: el campo está vacío.
- artículo en WordPress: está marcado como publicado y tiene `wp_post_id`, pero
  no conserva una URL válida en el panel.

Estado local actual:

| Señal | Resultado |
|---|---:|
| Negocios guardados | 312 |
| Con alguna carencia | 101 |
| Sin contacto | 12 |
| Ubicación incompleta | 58 |
| Sin imágenes locales | 39 |
| Sin tipo de comida | 41 |

Las categorías se solapan.

El frontend incorpora:

- tarjeta `Incompletos`;
- selector por tipo de carencia;
- contador de resultados;
- etiquetas rojas en cada ficha indicando exactamente qué falta.

Las fichas con contacto o ubicación incompletos muestran
`Actualizar datos desde Google`. La acción:

1. realiza una sola petición de detalles para el Place ID;
2. completa únicamente campos locales vacíos;
3. conserva las correcciones manuales existentes;
4. actualiza los campos ACF si el artículo sigue publicado;
5. refresca las etiquetas de la ficha.

## Reparación de enlaces

El post 42, `Reštaurácia Divný Janko`, existía en WordPress pero tenía
`article_path` vacío. Su permalink público se recuperó mediante la API de
WordPress y se guardó en SQLite. El botón `Ver artículo en WordPress` vuelve a
mostrarse para esa ficha.

Los otros ocho registros sin URL son las referencias a posts eliminados ya
inventariadas. Se muestran con la etiqueta `Sin artículo en WordPress` y no se
les fabrica un enlace que conduciría a un 404.

Para estas referencias desincronizadas, el panel muestra
`Volver a publicar en WordPress`. La acción reutiliza el artículo y las imágenes
locales, crea un post nuevo y sustituye el ID y la URL históricos.

También se ofrece `Pipeline completo: reparar y volver a publicar`, equivalente
al flujo de una publicación nueva:

1. obtiene o reutiliza las reseñas;
2. genera o recupera el artículo en caché;
3. descarga y registra imágenes sin duplicarlas;
4. selecciona la destacada;
5. crea el nuevo post y guarda su ID y URL.

## Validación y despliegue

- Backend compilado con Python sin errores.
- Build de producción de React/TypeScript completado.
- Backend sin puerto publicado al host.
- Único puerto público de la aplicación: frontend `8091`.
- Página principal servida correctamente.
- API sin sesión devuelve HTTP 401.
- Contenedores `backend` y `frontend` activos.
