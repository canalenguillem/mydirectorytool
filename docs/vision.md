# Visión del producto

## Propósito

Construir una herramienta privada que permita poner en marcha directorios verticales de negocios locales de forma rápida, controlada y reutilizable.

El producto inicial gestiona restaurantes y publica en `dondecomerbien.com`. La arquitectura futura debe permitir proyectos como peluquerías, talleres, gimnasios o profesionales, cada uno con su propio dominio, taxonomía, plantilla editorial y credenciales.

## Usuario principal

El usuario es el propietario u operador de uno o varios directorios. No es una plataforma pública de autoservicio para los negocios en esta fase.

El operador necesita:

- Buscar negocios por ciudad, distrito o consulta libre.
- Elegir cuáles incorpora; buscar nunca debe guardar automáticamente.
- Revisar datos de contacto y ubicación.
- Crear fichas y artículos sin escribirlos desde cero.
- Publicar a un ritmo seguro y pausable.
- Detectar fallos y reintentar sin duplicar contenido.
- Organizar negocios por territorio y categoría.
- Medir indexación, impresiones, clics y oportunidades SEO.

## Concepto de directorio

Un directorio es una configuración independiente:

```text
Nombre: Dónde comer bien
Sector: Restaurantes
Destino: https://dondecomerbien.com
Tipo de contenido: restaurante
Plantilla editorial: gastronomía
Campos: cocina, reservas, ubicación, contacto
Ritmo de publicación: configurable
```

Otro proyecto podría reutilizar el motor:

```text
Nombre: Peluquerías Mallorca
Sector: Peluquerías
Destino: https://otro-dominio.com
Tipo de contenido: peluqueria
Plantilla editorial: belleza y servicios
Campos: servicios, precios, reservas, ubicación, contacto
```

## Principios

### Selección antes de automatización

La herramienta puede descubrir muchos negocios, pero solo los seleccionados deben entrar en el directorio y consumir recursos de generación o publicación.

### Automatización observable

Todo proceso en segundo plano debe mostrar estado, próximo trabajo, intentos y último error. La automatización silenciosa dificulta corregir problemas.

### Idempotencia

Repetir una petición, pulsar dos veces o reiniciar el servidor no debe crear posts ni imágenes duplicadas.

### Datos estructurados antes que texto

Ciudad, provincia, país, coordenadas y contacto deben almacenarse como campos independientes. La dirección completa sigue siendo útil, pero no puede ser la única fuente geográfica.

### Coste controlado

Las llamadas a Google, OpenAI y WordPress deben ser explícitas, espaciadas, reutilizables mediante caché y resistentes a límites temporales.

### Calidad progresiva

Se empieza con revisión humana. La publicación totalmente automática solo se activa después de validar plantillas, datos y resultados en varios territorios.

## Resultado esperado

La versión madura permitirá dar de alta un directorio, conectar su WordPress, definir sus campos y prompts, buscar negocios por territorio y mantener una estructura pública como:

```text
Directorio
└── País
    └── Región o provincia
        └── Ciudad
            ├── Página de localidad
            ├── Categorías o servicios
            └── Fichas de negocios
```
