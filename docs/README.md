# Documentación de MyDirectoryTool

MyDirectoryTool es una herramienta para crear y mantener directorios de negocios locales con un alto grado de automatización. El primer caso de uso es el directorio gastronómico **Dónde comer bien**, pero el producto debe evolucionar para gestionar otros sectores y publicar cada proyecto en un WordPress diferente.

## Documentos

1. [Visión del producto](vision.md): objetivo, alcance y principios.
2. [Estado actual](current-state.md): qué está construido y qué limitaciones existen.
3. [Arquitectura](architecture.md): componentes, integraciones y flujo de información.
4. [Modelo de datos](data-model.md): entidades actuales y modelo multidirectorio propuesto.
5. [Operación](operations.md): despliegue, cola, búsquedas, seguridad y copias de respaldo.
6. [Contenido y SEO](content-and-seo.md): fichas, páginas geográficas y enlazado interno.
7. [Hoja de ruta](roadmap.md): fases recomendadas para convertir el MVP en una plataforma.
8. [Arquitectura de WordPress](wordpress-integration.md): reparto estable entre la herramienta, el plugin y el tema propio.
9. [Plan de implementación de WordPress](wordpress-implementation-plan.md): runbook completo de backups, plugin, taxonomías, tema propio, SEO, pruebas y reversión.
10. [Transformación de MyDirectoryTool](mydirectorytool-transformation-plan.md): evolución del MVP actual a una plataforma multidirectorio con asistente de alta.
11. [Migración a PostgreSQL](postgresql-migration-plan.md): estrategia ensayada para sustituir SQLite sin afectar WordPress ni perder la cola.

## Inventarios y puntos de restauración

- [Fase 0 · 23 de julio de 2026](inventories/2026-07-23-phase0.md): backup verificado, versiones, ACF, conteos y discrepancias detectadas.
- [Plugin 0.1.0 · 23 de julio de 2026](inventories/2026-07-23-plugin-scaffold.md): esqueleto inactivo, validación PHP y commit local.
- [Auditoría de contenido · 23 de julio de 2026](inventories/2026-07-23-content-quality-audit.md): títulos, extractos, datos incompletos, páginas débiles y política de indexación.

## Objetivo resumido

```text
Configurar un directorio
→ encontrar negocios
→ seleccionar fichas
→ enriquecer datos
→ generar contenido
→ publicar progresivamente
→ crear páginas de ciudad/categoría
→ medir resultados
→ mantener los datos actualizados
```

La automatización debe ahorrar trabajo repetitivo sin renunciar a control editorial, trazabilidad, costes previsibles ni protección frente a duplicados.
