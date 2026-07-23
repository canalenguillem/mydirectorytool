# Propuestas de mejora de títulos

Fecha: 23 de julio de 2026.

## Estado de la cola

Durante la primera exportación seguía activo el último lote de publicación. La
cola terminó a las 18:41 y WordPress quedó con 269 restaurantes publicados.

MyDirectoryTool conserva 276 negocios marcados como publicados. La diferencia
es coherente con las ocho referencias locales antiguas cuyo post ya no existe y
el post de WordPress sin registro local documentados en la fase 0:

```text
276 - 8 + 1 = 269
```

## Herramienta

`scripts/propose-wordpress-titles.py`

Entradas:

- Exportación de posts, URLs y taxonomías de WordPress.
- SQLite de MyDirectoryTool para recuperar el nombre real por `wp_post_id`.

Salida:

- título actual;
- propuesta;
- longitud actual y propuesta;
- negocio, localidad y cocina usados;
- motivo de la propuesta;
- URL de revisión.

La herramienta no incluye ninguna operación de escritura.

## Resultado

| Métrica | Resultado |
|---|---:|
| Posts recibidos | 269 |
| Negocios emparejados | 268 |
| Propuestas | 113 |
| Propuestas de más de 70 caracteres | 0 |
| Grupos de propuestas duplicadas | 0 |

El post no emparejado es el contenido huérfano de WordPress ya documentado.

## Ejemplos

| Actual | Propuesta |
|---|---|
| `Reštaurácia Divný Janko: Un Tesoro Escondido de la Cocina Eslovaca en Bratislava` | `Reštaurácia Divný Janko: cocina eslovaca y opiniones` |
| `Saborea la autenticidad en Bar Can Biel Felip: Un rincón culinario escondido en Palma de Mallorca` | `Bar Can Biel Felip: cocina mallorquina y opiniones` |
| `¿Por qué todo el mundo habla de Miga de Nube en Sóller?` | `Miga de nube: cocina mediterránea en Sóller` |
| `Paella con vistas al mar y sin trampa: así es Sa Caleta` | `Sa caleta en Cala Millor: cocina mediterránea` |
| `Paella con vistas al mar y sin trampa: así es Restaurante Amapola Brasas` | `RESTAURANTE AMAPOLA en Cala Millor: carnes a la brasa` |

## Reglas

- Se conserva el nombre procedente de la entidad real.
- Se evita repetir una localidad que ya forma parte del nombre.
- Se usan únicamente localidad y cocina existentes.
- Las categorías nominales reciben una redacción natural:
  `especialidad en carne`, `hamburguesas`, `tapas`, etc.
- Se busca un máximo de 65 caracteres y nunca se trunca el nombre comercial.
- Las fórmulas cambian según el patrón original para no crear otra serie
  completamente uniforme.

## Antes de aplicar

1. Revisar manualmente una muestra de diez propuestas.
2. Confirmar nombres comerciales con mayúsculas peculiares.
3. Aplicar solo `post_title`; conservar `post_name`.
4. Guardar backup SQL.
5. Verificar URL, H1, canonical, Open Graph y Schema.
6. Repetir auditoría y comparar CTR en Search Console.
