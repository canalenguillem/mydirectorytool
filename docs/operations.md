# Operación

## Arranque

```bash
docker compose up -d --build
```

Acceso local:

```text
http://localhost:8091
```

Solo el frontend publica puerto. Nginx reenvía `/api` al backend por la red interna.

## Variables principales

Consultar `backend/.env.example` para la lista completa:

```text
GOOGLE_API_KEY
OPENAI_API_KEY
WP_URL
WP_USER
WP_APP_PASS
DATA_DIR
CORS_ORIGINS
GOOGLE_DETAILS_DELAY_SECONDS
AUTH_USERNAME
AUTH_PASSWORD
AUTH_SECRET
AUTH_SESSION_SECONDS
AUTH_COOKIE_SECURE
```

En producción con HTTPS debe utilizarse `AUTH_COOKIE_SECURE=true`.

## Flujo recomendado de búsqueda

1. Buscar una ciudad o zona concreta.
2. Revisar los resultados.
3. Guardar únicamente negocios adecuados.
4. Confirmar ciudad, distrito, teléfono y web.
5. Incorporar los nuevos pendientes a la cola.

Consultas recomendadas:

```text
restaurantes Valencia centro
restaurantes Triana Sevilla
restaurantes Indautxu Bilbao
```

Evitar búsquedas demasiado amplias como `restaurantes España`.

## Consumo de Google

- Text Search se ejecuta una vez por consulta nueva.
- Place Details se ejecuta una vez por resultado nuevo.
- Las búsquedas quedan en caché por hash.
- La pausa entre detalles se configura con `GOOGLE_DETAILS_DELAY_SECONDS`.
- Un fallo puntual conserva el resultado básico y no detiene toda la búsqueda.
- No debe ejecutarse un enriquecimiento histórico masivo mientras la cola publica.

## Cola de publicación

Buenas prácticas:

- Probar primero con tres restaurantes después de cambios importantes.
- No pulsar repetidamente “Añadir todos los pendientes”.
- Revisar errores antes de reintentarlos.
- Pausar antes de desplegar cambios del pipeline.
- Si hay un trabajo procesándose, esperar a que termine antes de reiniciar.
- Mantener Docker y la máquina activos; el navegador puede cerrarse.

La estimación de cinco minutos por elemento no incluye el tiempo adicional que pueda tardar una operación externa lenta.

## WordPress y ACF

El grupo asociado al tipo `restaurante` utiliza actualmente:

```text
telefono
web
email
codigo_postal
ciudad
municipio
provincia
region
pais
codigo_pais
distrito
latitud
longitud
tipo_de_comida
place_id
place_gallery
```

Latitud y longitud deben ser campos numéricos con decimales. Las definiciones ACF se crean en WordPress; la aplicación solo escribe valores.

## Copias de seguridad

Contenido crítico:

```text
data/places.db
data/articles/
data/images/
```

Antes de migraciones o enriquecimientos masivos:

1. Pausar la cola.
2. Esperar a que `processing` sea cero.
3. Copiar `data/places.db` y, si procede, los archivos.
4. Verificar que la copia puede abrirse.
5. Ejecutar la operación por lotes pequeños.

## Observabilidad pendiente

Se debe incorporar:

- Logs estructurados sin secretos.
- Historial de cada llamada externa.
- Coste estimado por trabajo.
- Métricas de duración y tasa de errores.
- Alertas cuando la cola se detiene o acumula fallos.

## Incidentes

Si aparecen duplicados o publicaciones inesperadas:

1. Pausar la cola.
2. No borrar datos inmediatamente.
3. Identificar Place ID y post de WordPress.
4. Revisar estado local y medios asociados.
5. Corregir el flujo antes de reanudar.
