# mydirectorytool

Panel privado para gestionar restaurantes, generar artículos e imágenes y publicarlos en WordPress mediante una cola automática.

## Servicios

- Frontend React servido por Nginx en el puerto `8091`.
- Backend FastAPI accesible únicamente desde la red interna de Docker.
- Persistencia SQLite bajo `data/`.

## Inicio

1. Copia `backend/.env.example` a `backend/.env` y configura las integraciones.
2. Configura las credenciales locales de acceso.
3. Ejecuta `docker compose up -d --build`.
4. Abre `http://localhost:8091`.

Los archivos `.env`, bases de datos, imágenes y artículos generados están excluidos de Git.

## Documentación

La definición funcional y técnica del proyecto está en [`docs/`](docs/README.md):

- Visión del producto multidirectorio.
- Estado actual y funcionalidades terminadas.
- Arquitectura y modelo de datos.
- Operación segura de búsquedas y publicaciones.
- Estrategia SEO y páginas geográficas.
- Hoja de ruta hacia una plataforma reutilizable.
