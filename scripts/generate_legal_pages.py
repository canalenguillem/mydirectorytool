"""Genera y publica las páginas de Aviso Legal, Política de Privacidad y
Política de Cookies en un directorio WordPress de MyDirectoryTool.

Pensado para reutilizarse en cada nicho nuevo (Fase 4 del roadmap: "Página
de privacidad y aviso legal publicados" es parte de la barra de calidad de
monetización). Los datos de identidad del titular son fijos (misma persona
para todos los directorios); lo único que cambia por nicho es el nombre del
sitio, el dominio y, si hace falta, el correo de contacto.

Uso:
    WP_URL=https://tudirectorio.com WP_USER=... WP_APP_PASS=... \
    python scripts/generate_legal_pages.py --site-name "Mi Directorio" --domain tudirectorio.com

Si no se pasan credenciales por variable de entorno, usa las de
backend/.env (mismo patrón que backend/app/services/wordpress.py) para
poder ejecutarlo directamente contra dondecomerbien.com sin argumentos.
"""

import argparse
import os
import sys

import requests

# --- Identidad del titular (persona física, igual para todos los nichos) ---
TITULAR_NOMBRE = "Guillem Mateu"
TITULAR_NIF = "44326553X"
TITULAR_LOCALIDAD = "Palma, Illes Balears (España)"
CONTACT_EMAIL_DEFAULT = "infobasic2018@gmail.com"


def aviso_legal(site_name: str, domain: str, email: str) -> str:
    return f"""
<h2>1. Datos identificativos</h2>
<p>En cumplimiento del artículo 10 de la Ley 34/2002, de 11 de julio, de Servicios de la
Sociedad de la Información y de Comercio Electrónico (LSSI-CE), se informa de los
siguientes datos: el titular de este sitio web ({site_name}, accesible en
<a href="https://{domain}/">{domain}</a>) es <strong>{TITULAR_NOMBRE}</strong>, con NIF
<strong>{TITULAR_NIF}</strong>, con domicilio a efectos de notificaciones en {TITULAR_LOCALIDAD},
y correo electrónico de contacto <a href="mailto:{email}">{email}</a>.</p>

<h2>2. Objeto</h2>
<p>{site_name} es un directorio informativo que recopila y publica fichas de negocios
locales (nombre, ubicación, valoraciones, contacto y una descripción editorial) con el
fin de ayudar a los usuarios a encontrar opciones cerca de ellos. La información de cada
ficha se elabora a partir de datos públicos (como los publicados en Google Maps) y de
contenido editorial propio.</p>

<h2>3. Condiciones de uso</h2>
<p>El acceso y uso de este sitio web atribuye la condición de usuario y implica la
aceptación de las condiciones aquí recogidas. El usuario se compromete a hacer un uso
adecuado de los contenidos y servicios del sitio y a no emplearlos para incurrir en
actividades ilícitas, ilegales o contrarias a la buena fe y al orden público.</p>

<h2>4. Propiedad intelectual e industrial</h2>
<p>Los textos editoriales, el diseño, la estructura de navegación y el código de este
sitio web son propiedad de {TITULAR_NOMBRE}, salvo que se indique lo contrario. Los
nombres comerciales, marcas y logotipos de los negocios listados pertenecen a sus
respectivos titulares y se citan únicamente con fines informativos y de identificación,
sin que ello implique relación comercial alguna con este sitio salvo que se indique
expresamente.</p>

<h2>5. Exactitud de la información</h2>
<p>La información de cada ficha (horarios, valoraciones, datos de contacto) procede en
buena parte de fuentes de terceros y puede quedar desactualizada. Recomendamos
confirmar los datos relevantes (horario, disponibilidad) directamente con el negocio
antes de una visita. Si eres el titular de un negocio listado y quieres corregir o
solicitar la retirada de tu ficha, escríbenos a <a href="mailto:{email}">{email}</a>.</p>

<h2>6. Enlaces externos</h2>
<p>Este sitio puede incluir enlaces a páginas web de terceros (webs de los propios
negocios, redes sociales, Google Maps). {site_name} no se hace responsable del
contenido de dichos sitios ni de las políticas de privacidad que apliquen en ellos.</p>

<h2>7. Legislación aplicable</h2>
<p>Las presentes condiciones se rigen por la legislación española. Para cualquier
controversia derivada del acceso o uso de este sitio, y salvo que la normativa de
protección de consumidores establezca un fuero distinto, las partes se someten a los
juzgados y tribunales que correspondan según la ley.</p>
""".strip()


def politica_privacidad(site_name: str, domain: str, email: str) -> str:
    return f"""
<h2>1. Responsable del tratamiento</h2>
<p><strong>{TITULAR_NOMBRE}</strong> (NIF {TITULAR_NIF}), con domicilio a efectos de
notificaciones en {TITULAR_LOCALIDAD} y correo electrónico
<a href="mailto:{email}">{email}</a>, es el responsable del tratamiento de los datos
personales recogidos a través de {site_name} ({domain}).</p>

<h2>2. Qué datos recogemos y con qué finalidad</h2>
<ul>
<li><strong>Comentarios:</strong> si dejas un comentario en una ficha, guardamos el
nombre, correo electrónico y contenido que nos facilitas, así como tu dirección IP,
para poder publicarlo y moderar el spam (usamos Akismet para ese filtrado). Base legal:
tu consentimiento al enviar el comentario.</li>
<li><strong>Contacto directo por correo:</strong> si nos escribes a
<a href="mailto:{email}">{email}</a>, tratamos los datos que incluyas en tu mensaje
(nombre, correo, contenido) para responder a tu consulta. Base legal: tu consentimiento
al enviarnos el mensaje.</li>
<li><strong>Analítica del sitio:</strong> usamos Google Analytics (a través de Google
Site Kit) para entender cómo se usa el sitio (páginas vistas, procedencia del tráfico,
dispositivo aproximado), de forma agregada. Base legal: tu consentimiento, gestionado
mediante la configuración de cookies del navegador.</li>
<li><strong>Publicidad:</strong> si en el futuro este sitio muestra anuncios de Google
AdSense, Google podrá usar cookies para mostrar anuncios personalizados o no
personalizados según tu configuración de consentimiento. Base legal: tu consentimiento.</li>
</ul>

<h2>3. Destinatarios y transferencias internacionales</h2>
<p>No vendemos ni cedemos tus datos a terceros con fines comerciales propios. Compartimos
datos con los siguientes encargados/proveedores, en la medida necesaria para prestar el
servicio:</p>
<ul>
<li><strong>Google LLC</strong> (Google Analytics, Google Site Kit y, en su caso, Google
AdSense) — con sede en EE. UU., acogido a mecanismos de transferencia internacional
reconocidos por la normativa europea (como el Marco de Privacidad de Datos UE-EE. UU. o
cláusulas contractuales tipo).</li>
<li>El proveedor de <strong>alojamiento (hosting)</strong> de este sitio web, como
encargado técnico del tratamiento.</li>
</ul>

<h2>4. Conservación de los datos</h2>
<p>Los comentarios se conservan mientras la ficha a la que pertenecen siga publicada,
salvo que solicites su eliminación. Los correos de contacto se conservan el tiempo
necesario para resolver tu consulta y, salvo que exista obligación legal de conservarlos
más tiempo, se eliminan después.</p>

<h2>5. Tus derechos</h2>
<p>Puedes ejercer en cualquier momento tus derechos de acceso, rectificación, supresión,
oposición, limitación del tratamiento y portabilidad escribiendo a
<a href="mailto:{email}">{email}</a>, indicando el derecho que quieres ejercer y
adjuntando copia de un documento que acredite tu identidad. También tienes derecho a
presentar una reclamación ante la <a href="https://www.aepd.es/" target="_blank"
rel="noopener noreferrer">Agencia Española de Protección de Datos (AEPD)</a> si
consideras que el tratamiento no se ajusta a la normativa vigente.</p>

<h2>6. Medidas de seguridad</h2>
<p>Aplicamos medidas técnicas y organizativas razonables para proteger tus datos
personales frente a accesos no autorizados, pérdida o alteración, adecuadas al riesgo
del tratamiento realizado.</p>

<p>Para más detalle sobre las cookies concretas que usamos, consulta nuestra
<a href="/politica-de-cookies/">Política de Cookies</a>.</p>
""".strip()


def politica_cookies(site_name: str, domain: str, email: str) -> str:
    return f"""
<h2>1. Qué son las cookies</h2>
<p>Las cookies son pequeños archivos que un sitio web guarda en tu navegador para
recordar información sobre tu visita, como tus preferencias o cómo navegas por el
sitio.</p>

<h2>2. Cookies que usamos en {site_name}</h2>
<table>
<thead><tr><th>Tipo</th><th>Finalidad</th><th>Origen</th></tr></thead>
<tbody>
<tr><td>Técnicas / necesarias</td><td>Imprescindibles para el funcionamiento básico del
sitio (por ejemplo, recordar si has comentado antes).</td><td>Propias</td></tr>
<tr><td>Analíticas</td><td>Google Analytics (vía Google Site Kit): páginas vistas,
procedencia del tráfico, tiempo de navegación, de forma agregada.</td><td>Google LLC
(terceros)</td></tr>
<tr><td>Publicitarias</td><td>Si se activan anuncios de Google AdSense, se usarán para
mostrar publicidad personalizada o no personalizada según tu configuración.</td>
<td>Google LLC (terceros)</td></tr>
</tbody>
</table>

<h2>3. Cómo desactivar o gestionar las cookies</h2>
<p>Puedes permitir, bloquear o eliminar las cookies instaladas en tu navegador
configurando las opciones de tu navegador (Chrome, Firefox, Safari, Edge, etc.). Ten en
cuenta que bloquear algunas cookies puede afectar al funcionamiento del sitio.</p>
<p>Para las cookies de Google puedes gestionar tus preferencias de anuncios directamente
en <a href="https://myadcenter.google.com/" target="_blank" rel="noopener noreferrer">la
configuración de anuncios de Google</a>, o consultar
<a href="https://policies.google.com/technologies/cookies" target="_blank"
rel="noopener noreferrer">cómo usa Google las cookies</a>.</p>

<h2>4. Contacto</h2>
<p>Si tienes cualquier duda sobre esta política de cookies, escríbenos a
<a href="mailto:{email}">{email}</a>.</p>
""".strip()


def publish_or_update_page(wp_url: str, auth: tuple, slug: str, title: str, content: str) -> int:
    search = requests.get(f"{wp_url}/wp-json/wp/v2/pages", auth=auth, params={"slug": slug})
    search.raise_for_status()
    existing = search.json()

    payload = {"title": title, "content": content, "status": "publish", "slug": slug}
    if existing:
        page_id = existing[0]["id"]
        r = requests.post(f"{wp_url}/wp-json/wp/v2/pages/{page_id}", auth=auth, json=payload)
    else:
        r = requests.post(f"{wp_url}/wp-json/wp/v2/pages", auth=auth, json=payload)
    r.raise_for_status()
    return r.json()["id"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-name", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--email", default=CONTACT_EMAIL_DEFAULT)
    args = parser.parse_args()

    wp_url = os.environ.get("WP_URL")
    wp_user = os.environ.get("WP_USER")
    wp_app_pass = os.environ.get("WP_APP_PASS")
    if not (wp_url and wp_user and wp_app_pass):
        sys.path.insert(0, "/app")
        from decouple import config
        wp_url = wp_url or config("WP_URL")
        wp_user = wp_user or config("WP_USER")
        wp_app_pass = wp_app_pass or config("WP_APP_PASS")
    auth = (wp_user, wp_app_pass)

    pages = [
        ("aviso-legal", "Aviso Legal", aviso_legal(args.site_name, args.domain, args.email)),
        ("politica-de-privacidad", "Política de Privacidad", politica_privacidad(args.site_name, args.domain, args.email)),
        ("politica-de-cookies", "Política de Cookies", politica_cookies(args.site_name, args.domain, args.email)),
    ]

    ids = {}
    for slug, title, content in pages:
        page_id = publish_or_update_page(wp_url, auth, slug, title, content)
        ids[slug] = page_id
        print(f"{title}: id={page_id} -> {wp_url}/{slug}/")

    print("IDS_JSON", ids)


if __name__ == "__main__":
    main()
