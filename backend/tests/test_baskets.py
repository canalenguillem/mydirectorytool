from app.models import database
from app.services import place_deletion
from tests.conftest import insert_place


def test_create_and_list_baskets(temp_db):
    basket = database.create_basket("pasta palma")

    assert basket["name"] == "pasta palma"
    baskets = database.list_baskets()
    assert len(baskets) == 1
    assert baskets[0]["id"] == basket["id"]
    assert baskets[0]["place_count"] == 0


def test_add_and_get_basket_places(temp_db, conn):
    insert_place(conn, "p1", name="Pasta e Pesto")
    insert_place(conn, "p2", name="Gigi's")
    basket = database.create_basket("pasta palma")

    database.add_place_to_basket(basket["id"], "p1")
    database.add_place_to_basket(basket["id"], "p2")

    detail = database.get_basket(basket["id"])
    assert detail["name"] == "pasta palma"
    assert [p["place_id"] for p in detail["places"]] == ["p1", "p2"]

    baskets = database.list_baskets()
    assert baskets[0]["place_count"] == 2


def test_add_place_to_basket_is_idempotent(temp_db, conn):
    insert_place(conn, "p1")
    basket = database.create_basket("cesta")

    database.add_place_to_basket(basket["id"], "p1")
    database.add_place_to_basket(basket["id"], "p1")

    detail = database.get_basket(basket["id"])
    assert len(detail["places"]) == 1


def test_remove_place_from_basket(temp_db, conn):
    insert_place(conn, "p1")
    basket = database.create_basket("cesta")
    database.add_place_to_basket(basket["id"], "p1")

    database.remove_place_from_basket(basket["id"], "p1")

    detail = database.get_basket(basket["id"])
    assert detail["places"] == []


def test_get_basket_returns_none_for_missing_id(temp_db):
    assert database.get_basket(999) is None


def test_delete_basket_removes_basket_and_its_places(temp_db, conn):
    insert_place(conn, "p1")
    basket = database.create_basket("cesta")
    database.add_place_to_basket(basket["id"], "p1")

    database.delete_basket(basket["id"])

    assert database.get_basket(basket["id"]) is None
    assert database.list_baskets() == []


def test_deleting_a_place_removes_it_from_baskets(temp_db, conn, monkeypatch):
    monkeypatch.setattr(place_deletion, "DB_PATH", temp_db)
    insert_place(conn, "p1", name="Pasta e Pesto")
    insert_place(conn, "p2", name="Gigi's")
    basket = database.create_basket("cesta")
    database.add_place_to_basket(basket["id"], "p1")
    database.add_place_to_basket(basket["id"], "p2")

    place_deletion.delete_place_completely("p1")

    detail = database.get_basket(basket["id"])
    assert [p["place_id"] for p in detail["places"]] == ["p2"]
    orphan_rows = conn.execute(
        "SELECT * FROM basket_place WHERE place_id = 'p1'"
    ).fetchall()
    assert orphan_rows == []
