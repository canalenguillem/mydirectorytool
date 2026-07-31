def select_top_candidates(
    candidates: list[dict],
    top_n: int = 20,
    min_user_ratings: int = 15,
) -> list[dict]:
    """Selecciona los top_n candidatos por rating (desempate por
    user_ratings_total), exigiendo un mínimo de reseñas para entrar en el
    corte principal -- evita que un 5.0 con 1 reseña gane a un 4.6 con 500.
    Si no hay suficientes candidatos cualificados, rellena con los
    siguientes mejor valorados (sin exigir el umbral) para no devolver
    menos de top_n en ciudades con poca oferta. Excluye negocios cerrados
    permanentemente y candidatos sin rating."""
    rated = [
        c
        for c in candidates
        if c.get("rating") is not None
        and c.get("business_status") != "CLOSED_PERMANENTLY"
    ]

    qualified = [
        c for c in rated if (c.get("user_ratings_total") or 0) >= min_user_ratings
    ]
    qualified.sort(
        key=lambda c: (c["rating"], c.get("user_ratings_total") or 0), reverse=True
    )
    if len(qualified) >= top_n:
        return qualified[:top_n]

    qualified_ids = {c["place_id"] for c in qualified}
    leftover = [c for c in rated if c["place_id"] not in qualified_ids]
    leftover.sort(
        key=lambda c: (c.get("user_ratings_total") or 0, c["rating"]), reverse=True
    )
    return qualified + leftover[: top_n - len(qualified)]
