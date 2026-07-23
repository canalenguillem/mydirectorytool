#!/usr/bin/env python3
"""Propone títulos más claros sin modificar WordPress ni sus URLs."""

from __future__ import annotations

import argparse
import html
import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any


PATTERNS = {
    "lo_mejor_segun_clientes": r"^lo mejor de .+, segun quienes ya se han sentado a su mesa$",
    "todo_el_mundo_habla": r"^¿?por que todo el mundo habla de .+\??$",
    "paella_sin_trampa": r"^paella con vistas al mar y sin trampa: asi es ",
    "propuesta_con_sello": r": una propuesta gastronomica con sello propio$",
    "parada_para_recordar": r": una parada gastronomica para recordar$",
    "conviene_saber": r"^comer en .+: lo que conviene saber antes de ir$",
    "vale_la_pena": r"^vale la pena comer en .+[:?] esto dicen sus clientes$",
    "experiencia_al_detalle": r": una experiencia contada al detalle$",
}


def normalize(value: str) -> str:
    value = html.unescape(value).strip().lower()
    value = unicodedata.normalize("NFKD", value)
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", value)


def load_businesses(database: Path) -> dict[int, dict[str, str]]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    rows = connection.execute(
        """
        SELECT wp_post_id, name, municipality, city, tipo_de_comida
        FROM place
        WHERE wp_post_id IS NOT NULL
          AND publicado_en_wp = 1
        """
    ).fetchall()
    connection.close()

    return {
        int(row["wp_post_id"]): {
            "name": (row["name"] or "").strip(),
            "municipality": (row["municipality"] or row["city"] or "").strip(),
            "cuisine": (row["tipo_de_comida"] or "").strip(),
        }
        for row in rows
    }


def classify(title: str) -> str | None:
    normalized = normalize(title)

    for name, pattern in PATTERNS.items():
        if re.search(pattern, normalized):
            return name

    return None


def cuisine_descriptor(cuisine: str) -> str:
    normalized = normalize(cuisine)
    descriptors = {
        "brunch": "brunch",
        "cafeteria": "cafetería",
        "carne": "especialidad en carne",
        "carnes": "especialidad en carne",
        "carnes a la brasa": "carnes a la brasa",
        "hamburguesas": "hamburguesas",
        "parrilla": "parrilla",
        "tapas": "tapas",
    }

    return descriptors.get(normalized, f"cocina {cuisine.lower()}")


def choose_title(
    name: str,
    municipality: str,
    cuisine: str,
    pattern: str | None,
) -> str:
    name = html.unescape(name).strip()
    municipality = html.unescape(municipality).strip()
    cuisine = html.unescape(cuisine).strip().lower()

    if municipality and normalize(municipality) in normalize(name):
        municipality = ""

    candidates: list[str] = []
    descriptor = cuisine_descriptor(cuisine) if cuisine else ""

    if pattern == "lo_mejor_segun_clientes" and municipality:
        candidates.append(f"{name} en {municipality}: guía y opiniones")
    elif pattern == "todo_el_mundo_habla" and municipality and descriptor:
        candidates.append(f"{name}: {descriptor} en {municipality}")
    elif pattern == "paella_sin_trampa" and municipality and descriptor:
        candidates.append(f"{name} en {municipality}: {descriptor}")
    elif pattern == "propuesta_con_sello" and descriptor:
        candidates.append(f"{name}: {descriptor} y ambiente")
    elif pattern == "parada_para_recordar" and municipality:
        candidates.append(f"{name} en {municipality}: guía práctica")
    elif pattern == "conviene_saber":
        candidates.append(f"{name}: qué pedir y qué debes saber")
    elif pattern == "vale_la_pena":
        candidates.append(f"{name}: guía, ambiente y opiniones")
    elif pattern == "experiencia_al_detalle" and municipality:
        candidates.append(f"{name} en {municipality}: carta y ambiente")

    if municipality and cuisine:
        candidates.extend(
            [
                f"{name} en {municipality}: {descriptor} y opiniones",
                f"{name}: {descriptor} en {municipality}",
            ]
        )

    if municipality:
        candidates.extend(
            [
                f"{name} en {municipality}: guía y opiniones",
                f"{name} en {municipality}",
            ]
        )

    if cuisine:
        candidates.append(f"{name}: {descriptor} y opiniones")

    candidates.extend([f"{name}: guía y opiniones", name])

    for candidate in candidates:
        if len(candidate) <= 65:
            return candidate

    return name


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wordpress-json", required=True, type=Path)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    posts: list[dict[str, Any]] = json.loads(
        args.wordpress_json.read_text(encoding="utf-8")
    )
    businesses = load_businesses(args.database)
    proposals: list[dict[str, Any]] = []

    for post in posts:
        post_id = int(post["post_id"])
        current = html.unescape(str(post["title"])).strip()
        pattern = classify(current)
        reasons: list[str] = []

        if len(current) > 70:
            reasons.append("long_title")

        if pattern:
            reasons.append(f"template:{pattern}")

        if not reasons:
            continue

        business = businesses.get(post_id, {})
        name = business.get("name", "")

        if not name:
            continue

        municipalities = post.get("municipalities") or []
        cuisines = post.get("cuisines") or []
        municipality = (
            str(municipalities[0]).strip()
            if municipalities
            else business.get("municipality", "")
        )
        cuisine = (
            str(cuisines[0]).strip()
            if cuisines
            else business.get("cuisine", "")
        )
        proposed = choose_title(name, municipality, cuisine, pattern)

        if normalize(proposed) == normalize(current):
            continue

        proposals.append(
            {
                "post_id": post_id,
                "url": post["url"],
                "business_name": name,
                "municipality": municipality,
                "cuisine": cuisine,
                "current_title": current,
                "current_length": len(current),
                "proposed_title": proposed,
                "proposed_length": len(proposed),
                "reasons": reasons,
                "source": "sqlite_place.wp_post_id",
            }
        )

    normalized_proposals: dict[str, list[int]] = {}

    for proposal in proposals:
        key = normalize(proposal["proposed_title"])
        normalized_proposals.setdefault(key, []).append(proposal["post_id"])

    duplicate_proposals = {
        title: post_ids
        for title, post_ids in normalized_proposals.items()
        if len(post_ids) > 1
    }
    report = {
        "mode": "proposal_only",
        "posts_received": len(posts),
        "businesses_matched": sum(
            1 for post in posts if int(post["post_id"]) in businesses
        ),
        "proposals": len(proposals),
        "proposals_over_70_chars": sum(
            1 for proposal in proposals if proposal["proposed_length"] > 70
        ),
        "duplicate_proposal_groups": duplicate_proposals,
        "items": proposals,
    }
    payload = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
