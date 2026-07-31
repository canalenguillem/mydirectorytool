from app.services.place_ranking import select_top_candidates


def _candidate(place_id, rating, user_ratings_total, business_status="OPERATIONAL"):
    return {
        "place_id": place_id,
        "rating": rating,
        "user_ratings_total": user_ratings_total,
        "business_status": business_status,
    }


def test_returns_top_n_by_rating_with_count_tiebreak():
    candidates = [
        _candidate("a", 4.2, 500),
        _candidate("b", 4.8, 100),
        _candidate("c", 4.8, 300),  # mismo rating que b, mas resenas -> antes
        _candidate("d", 3.9, 1000),
    ]

    top = select_top_candidates(candidates, top_n=3, min_user_ratings=15)

    assert [c["place_id"] for c in top] == ["c", "b", "a"]


def test_min_user_ratings_excludes_noisy_high_rating():
    candidates = [
        _candidate("noisy_five_star", 5.0, 1),  # solo 1 resena, no cualifica
        _candidate("solid", 4.6, 500),
    ]

    top = select_top_candidates(candidates, top_n=2, min_user_ratings=15)

    # el ruidoso entra de relleno (no hay 2 cualificados) pero detras del solido
    assert [c["place_id"] for c in top] == ["solid", "noisy_five_star"]


def test_backfills_when_not_enough_qualified_candidates():
    candidates = [_candidate("only_one", 4.9, 500)]

    top = select_top_candidates(candidates, top_n=20, min_user_ratings=15)

    assert len(top) == 1
    assert top[0]["place_id"] == "only_one"


def test_excludes_permanently_closed():
    candidates = [
        _candidate("open", 4.5, 100),
        _candidate("closed", 5.0, 1000, business_status="CLOSED_PERMANENTLY"),
    ]

    top = select_top_candidates(candidates, top_n=20, min_user_ratings=15)

    assert [c["place_id"] for c in top] == ["open"]


def test_excludes_candidates_without_rating():
    candidates = [
        _candidate("rated", 4.5, 100),
        {"place_id": "unrated", "rating": None, "user_ratings_total": 500, "business_status": "OPERATIONAL"},
    ]

    top = select_top_candidates(candidates, top_n=20, min_user_ratings=15)

    assert [c["place_id"] for c in top] == ["rated"]


def test_empty_candidates_returns_empty():
    assert select_top_candidates([], top_n=20, min_user_ratings=15) == []


def test_does_not_return_more_than_top_n():
    candidates = [_candidate(f"p{i}", 4.0 + i * 0.01, 100) for i in range(30)]

    top = select_top_candidates(candidates, top_n=20, min_user_ratings=15)

    assert len(top) == 20
    # el mejor valorado (p29) debe estar primero
    assert top[0]["place_id"] == "p29"
