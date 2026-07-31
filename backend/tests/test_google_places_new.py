import requests

from app.services import google_places_new as gpn


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.HTTPError(f"{self.status_code} error")
            error.response = self
            raise error

    def json(self):
        return self._payload


def _place(place_id, name="Restaurante", rating=4.5, user_ratings_total=100, lat=39.5, lng=2.6):
    return {
        "id": place_id,
        "displayName": {"text": name},
        "formattedAddress": "Calle Falsa 123",
        "rating": rating,
        "userRatingCount": user_ratings_total,
        "businessStatus": "OPERATIONAL",
        "location": {"latitude": lat, "longitude": lng},
    }


# --- search_text_new ---------------------------------------------------------

def test_search_text_new_sends_expected_headers_and_body(monkeypatch):
    captured = {}

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return _FakeResponse({"places": []})

    monkeypatch.setattr(gpn.requests, "post", fake_post)
    monkeypatch.setattr(gpn, "config", lambda key: "fake-api-key")

    gpn.search_text_new("restaurantes en Palma")

    assert captured["url"] == gpn.TEXT_SEARCH_URL
    assert captured["headers"]["X-Goog-Api-Key"] == "fake-api-key"
    assert captured["headers"]["X-Goog-FieldMask"] == gpn.DISCOVERY_FIELD_MASK
    assert captured["json"]["textQuery"] == "restaurantes en Palma"
    assert "pageToken" not in captured["json"]


def test_search_text_new_includes_page_token_when_given(monkeypatch):
    captured = {}
    monkeypatch.setattr(
        gpn.requests, "post",
        lambda url, headers=None, json=None, timeout=None: captured.update(json=json) or _FakeResponse({"places": []}),
    )
    monkeypatch.setattr(gpn, "config", lambda key: "fake-api-key")

    gpn.search_text_new("query", page_token="abc123")

    assert captured["json"]["pageToken"] == "abc123"


# --- discover_candidates -------------------------------------------------------

def test_discover_candidates_stops_when_no_next_page_token(monkeypatch, temp_db):
    monkeypatch.setattr(
        gpn, "search_text_new", lambda query, page_token=None: {"places": [_place("p1")]}
    )
    monkeypatch.setattr(gpn.time, "sleep", lambda seconds: None)

    results = gpn.discover_candidates("restaurantes en Palma", max_pages=3)

    assert [p["id"] for p in results] == ["p1"]


def test_discover_candidates_pages_up_to_max_pages(monkeypatch, temp_db):
    calls = []

    def fake_search(query, page_token=None):
        calls.append(page_token)
        page_num = len(calls)
        return {
            "places": [_place(f"p{page_num}")],
            "nextPageToken": f"token{page_num}",
        }

    monkeypatch.setattr(gpn, "search_text_new", fake_search)
    monkeypatch.setattr(gpn.time, "sleep", lambda seconds: None)

    results = gpn.discover_candidates("restaurantes en Palma", max_pages=3)

    assert len(calls) == 3
    assert [p["id"] for p in results] == ["p1", "p2", "p3"]


def test_discover_candidates_deduplicates_by_id(monkeypatch, temp_db):
    monkeypatch.setattr(
        gpn, "search_text_new",
        lambda query, page_token=None: {"places": [_place("dup"), _place("dup"), _place("unique")]},
    )
    monkeypatch.setattr(gpn.time, "sleep", lambda seconds: None)

    results = gpn.discover_candidates("restaurantes en Palma", max_pages=1)

    assert sorted(p["id"] for p in results) == ["dup", "unique"]


def test_discover_candidates_sleeps_between_pages(monkeypatch, temp_db):
    sleeps = []

    def fake_search(query, page_token=None):
        page_num = len(sleeps) + 1 if sleeps else 1
        if page_num == 1 and page_token is None:
            return {"places": [_place("p1")], "nextPageToken": "tok"}
        return {"places": [_place("p2")]}

    monkeypatch.setattr(gpn, "search_text_new", fake_search)
    monkeypatch.setattr(gpn.time, "sleep", lambda seconds: sleeps.append(seconds))

    gpn.discover_candidates("restaurantes en Palma", max_pages=3)

    assert len(sleeps) == 1  # solo entre paginas, no tras la ultima


def test_discover_candidates_records_usage_on_success(monkeypatch, temp_db, conn):
    monkeypatch.setattr(
        gpn, "search_text_new", lambda query, page_token=None: {"places": [_place("p1")]}
    )

    gpn.discover_candidates(
        "restaurantes en Palma", max_pages=1, seed_location_id=1,
        country_code="ES", directory_search_term="restaurantes",
    )

    row = conn.execute(
        "SELECT operation, result_count, status, country_code FROM google_places_usage"
    ).fetchone()
    assert row["operation"] == "text_search_new"
    assert row["result_count"] == 1
    assert row["status"] == "OK"
    assert row["country_code"] == "ES"


def test_discover_candidates_records_usage_on_error_and_reraises(monkeypatch, temp_db, conn):
    def fake_search(query, page_token=None):
        raise requests.HTTPError("boom")

    monkeypatch.setattr(gpn, "search_text_new", fake_search)

    try:
        gpn.discover_candidates("restaurantes en Palma", max_pages=1)
        assert False, "deberia haber relanzado la excepcion"
    except requests.HTTPError:
        pass

    row = conn.execute("SELECT status, result_count FROM google_places_usage").fetchone()
    assert row["status"] == "ERROR"
    assert row["result_count"] == 0


# --- normalize_candidate -------------------------------------------------------

def test_normalize_candidate_maps_new_shape_to_legacy_shape():
    place = _place("p1", name="Casa Pepe", rating=4.7, user_ratings_total=250, lat=39.1, lng=2.2)

    normalized = gpn.normalize_candidate(place)

    assert normalized["place_id"] == "p1"
    assert normalized["name"] == "Casa Pepe"
    assert normalized["formatted_address"] == "Calle Falsa 123"
    assert normalized["rating"] == 4.7
    assert normalized["user_ratings_total"] == 250
    assert normalized["business_status"] == "OPERATIONAL"
    assert normalized["geometry"]["location"] == {"lat": 39.1, "lng": 2.2}
