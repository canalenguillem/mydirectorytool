from app.services import google_places_usage as gpu


def test_record_inserts_row(temp_db, conn):
    gpu.record_google_places_usage(
        "text_search_new", "v1", field_mask="places.id", query="restaurantes en Palma",
        seed_location_id=1, country_code="ES", directory_search_term="restaurantes",
        result_count=20, status="OK", place_id=None,
    )

    row = conn.execute("SELECT * FROM google_places_usage").fetchone()
    assert row["operation"] == "text_search_new"
    assert row["endpoint_version"] == "v1"
    assert row["result_count"] == 20
    assert row["status"] == "OK"
    assert row["country_code"] == "ES"


def test_record_never_raises_on_db_error(temp_db, monkeypatch):
    monkeypatch.setattr(gpu, "DB_PATH", "/ruta/que/no/existe/places.db")

    # No debe lanzar excepcion, solo loggear un warning (mismo patron que
    # record_openai_usage).
    gpu.record_google_places_usage("text_search_new", "v1")


def test_get_usage_summary_aggregates_by_operation(temp_db, conn):
    gpu.record_google_places_usage("text_search_new", "v1", result_count=20, status="OK")
    gpu.record_google_places_usage("text_search_new", "v1", result_count=15, status="OK")
    gpu.record_google_places_usage("place_details", "legacy", result_count=1, status="OK")

    summary = gpu.get_google_places_usage_summary(days=30)

    assert summary["requests"] == 3
    assert summary["results"] == 36
    breakdown = {row["operation"]: row for row in summary["breakdown"]}
    assert breakdown["text_search_new"]["requests"] == 2
    assert breakdown["text_search_new"]["results"] == 35
    assert breakdown["place_details"]["requests"] == 1


def test_get_usage_summary_excludes_old_rows_outside_window(temp_db, conn):
    import time

    conn.execute(
        """
        INSERT INTO google_places_usage (created_at, operation, endpoint_version, result_count, status)
        VALUES (?, 'text_search_new', 'v1', 20, 'OK')
        """,
        (int(time.time()) - 40 * 86400,),
    )
    conn.commit()
    gpu.record_google_places_usage("text_search_new", "v1", result_count=5, status="OK")

    summary = gpu.get_google_places_usage_summary(days=30)

    assert summary["requests"] == 1
    assert summary["results"] == 5
