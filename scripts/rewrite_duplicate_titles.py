"""Reescritura retroactiva de títulos/artículos con plantilla repetida.

Contexto: la auditoría de 2026-07-30 (docs/inventories/2026-07-30-title-rewrite.md)
encontró 86 fichas publicadas antes del arreglo de variedad de títulos
(commit 559ec51, 26-27 julio) que siguen usando una de 7 plantillas
casi idénticas. El arreglo de esa semana solo afecta a artículos nuevos
-- este script regenera esas 86 con el sistema actual (59 plantillas,
6 ángulos retóricos, selección determinista por place_id) y actualiza
el post YA PUBLICADO en WordPress (título + contenido + extracto),
sin crear posts nuevos ni tocar ACF/imágenes/tipo de comida.

Uso (dentro del contenedor backend, con acceso a OpenAI y WordPress):
    python scripts/rewrite_duplicate_titles.py targets.json [--limit N] [--dry-run]

`targets.json`: lista de objetos {"place_id": ..., "post_id": ...} (o con
más campos, se ignoran). Generado por scripts/dump_duplicate_titles.php
+ cruce contra la tabla place -- ver el inventario para el procedimiento
completo.
"""

import argparse
import hashlib
import html
import json
import logging
import re
import sqlite3
import sys
import time

sys.path.insert(0, "/app")  # mismo layout que el resto de scripts ejecutados en el contenedor

from app.models.database import DB_PATH, delete_article, get_or_create_article, get_or_create_review_info
from app.services.openai_writer import TITLE_PATTERNS, aplicar_titulo, generar_articulo_blog, generar_excerpt
from app.services.wordpress import actualizar_articulo_restaurante, markdown_a_html_restaurante

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("rewrite_duplicate_titles")

# 4 de las 59 plantillas de TITLE_PATTERNS son literalmente las mismas que
# ya causaban la repetición en las fichas antiguas (solo se retiró la peor,
# "Lo mejor de {name}...", al añadir variedad el 26 de julio). Para ESTA
# reescritura retroactiva las vetamos explícitamente -- si la selección
# determinista por place_id cae en una de ellas, se sustituye por la
# siguiente plantilla no vetada (mismo hash base, desplazamiento
# determinista, no aleatorio). No se toca TITLE_PATTERNS ni el hash
# compartido con el resto de la app.
PLANTILLAS_VETADAS = {
    "Comer en {name}: lo que conviene saber antes de ir",
    "{name}: una parada gastronómica para recordar",
    "{name} en {locality}: una experiencia contada al detalle",
    "{name}: una propuesta gastronómica con sello propio",
}


def _locality_normalizada(info: dict) -> str:
    locality = " ".join(str(info.get("locality") or "la zona").split())
    if "balear" in locality.lower():
        locality = "Mallorca"
    return locality


def titulo_esta_vetado(title: str, name: str, locality: str) -> bool:
    return any(t.format(name=name, locality=locality) == title for t in PLANTILLAS_VETADAS)


SAFE_TEMPLATES = [t for t in TITLE_PATTERNS if t not in PLANTILLAS_VETADAS]


def elegir_titulo_alternativo(place_id: str, name: str, locality: str) -> str:
    """Recalcula con una sal distinta (no un simple 'siguiente índice'):
    si todas las fichas que compartían la misma plantilla vetada avanzaran
    al mismo índice siguiente, solo trasladaríamos el duplicado a otro
    sitio en vez de repartirlo. Al re-hashear con sal propia por place_id
    sobre la lista de plantillas seguras, cada ficha cae en una posición
    distinta."""
    stable_key = (place_id or name) + "::title_retry"
    idx = int(hashlib.sha256(stable_key.encode()).hexdigest()[:8], 16) % len(SAFE_TEMPLATES)
    return SAFE_TEMPLATES[idx].format(name=name, locality=locality)


def extraer_titulo(md_text: str) -> str:
    match = re.search(r"^# (.+)", md_text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def quitar_titulo(md_text: str) -> str:
    if md_text.startswith("# "):
        _, *rest = md_text.split("\n", 1)
        return rest[0] if rest else ""
    return md_text


def reescribir_uno(place_id: str, post_id: int, old_title: str, dry_run: bool) -> dict:
    info = get_or_create_review_info(place_id)
    delete_article(place_id, "es")
    new_md = get_or_create_article(info, "es", generar_articulo_blog)

    new_title = extraer_titulo(new_md)
    name = " ".join(str(info.get("name") or "Restaurante").split())
    locality = _locality_normalizada(info)
    overridden = False

    if titulo_esta_vetado(new_title, name, locality):
        alt_title = elegir_titulo_alternativo(place_id, name, locality)
        new_md = aplicar_titulo(new_md, alt_title)
        new_title = alt_title
        overridden = True
        # Persistir el título corregido en el .md cacheado -- si no,
        # get_or_create_article seguiría sirviendo el título vetado desde
        # disco la próxima vez que se lea esta ficha.
        with sqlite3.connect(DB_PATH) as conn:
            row = conn.execute(
                "SELECT path FROM blog_article WHERE place_id = ? AND lang = 'es'", (place_id,)
            ).fetchone()
        if row and row[0]:
            with open(row[0], "w", encoding="utf-8") as f:
                f.write(new_md)

    content_for_excerpt = quitar_titulo(new_md)
    html_content = markdown_a_html_restaurante(new_md)
    excerpt = generar_excerpt(content_for_excerpt, place_id)

    result = {
        "place_id": place_id,
        "post_id": post_id,
        "old_title": old_title,
        "new_title": new_title,
        "same_title": html.unescape(old_title).strip() == new_title.strip(),
        "title_overridden": overridden,
    }

    if dry_run:
        result["updated"] = False
        return result

    result["updated"] = actualizar_articulo_restaurante(post_id, new_title, html_content, excerpt)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("targets", help="JSON con [{place_id, post_id, title}, ...]")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--delay", type=float, default=1.0)
    args = parser.parse_args()

    targets = json.load(open(args.targets, encoding="utf-8"))
    if args.limit:
        targets = targets[: args.limit]

    results = []
    for i, item in enumerate(targets, 1):
        place_id = item["place_id"]
        post_id = item["post_id"]
        old_title = item.get("title", "")
        logger.info(f"[{i}/{len(targets)}] {place_id} (post {post_id}) -- {old_title[:60]}")
        try:
            result = reescribir_uno(place_id, post_id, old_title, args.dry_run)
        except Exception as exc:
            logger.exception(f"Fallo en {place_id}")
            result = {"place_id": place_id, "post_id": post_id, "old_title": old_title, "error": str(exc)}
        results.append(result)
        logger.info(f"  -> {result.get('new_title', 'ERROR')!r} (updated={result.get('updated')})")
        if args.delay > 0 and i < len(targets):
            time.sleep(args.delay)

    out_path = args.targets.replace(".json", "_results.json")
    json.dump(results, open(out_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    ok = sum(1 for r in results if r.get("updated"))
    errors = sum(1 for r in results if "error" in r)
    same = sum(1 for r in results if r.get("same_title"))
    logger.info(f"Terminado: {ok} actualizados, {errors} errores, {same} con el mismo título que antes.")
    logger.info(f"Resultados detallados en {out_path}")


if __name__ == "__main__":
    main()
