# Muestra aplicada de títulos

Fecha: 23 de julio de 2026.

## Alcance

Se aplicaron diez propuestas del informe
`2026-07-23-title-proposals.md`. La operación modificó únicamente el
`post_title` de cada restaurante. No se regeneraron slugs ni se cambiaron
permalinks.

IDs tratados:

```text
42, 53, 65, 111, 184, 244, 256, 268, 431, 593
```

## Copia de seguridad

Dump previo de `wp_posts`:

```text
/home/guillem/backups/dondecomerbien/2026-07-23_pre_title_sample/wordpress-posts.sql
```

SHA-256:

```text
34c8b596c82582001a11f890a920c206faf6c048f76f342209d052bf364ced2c
```

El volcado terminó correctamente antes de realizar ninguna escritura.

## Controles aplicados

- Preflight global: los diez IDs debían existir, ser `restaurante` y conservar
  exactamente el título esperado.
- La primera validación detectó diferencias tipográficas y se detuvo sin
  escribir; se corrigieron los valores esperados antes de repetirla.
- Tras cada actualización se comprobó el título, el `post_name` y el permalink.
- Los diez slugs y las diez URLs permanecieron sin cambios.
- Tres URLs de muestra devolvieron HTTP 200.
- En la web pública se comprobó el nuevo H1, Open Graph, Schema y canonical.
- Se detectaron ocho H1 antiguos duplicados dentro del contenido. Se retiraron
  solo cuando coincidían exactamente con el título anterior.
- Las páginas revisadas quedaron con un único H1.

## Resultado

La muestra permite cambiar títulos editoriales sin perder URLs históricas. No
debe aplicarse el resto en bloque hasta revisar el resultado visual y esperar
datos suficientes en Search Console para comparar impresiones, CTR y posición.

