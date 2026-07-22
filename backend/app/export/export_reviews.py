import sqlite3
import json
import os

DB_PATH = "places.db"
OUTPUT_DIR = "exports"

os.makedirs(OUTPUT_DIR, exist_ok=True)

def exportar_reviews():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Llistem tots els llocs que tenen ressenyes
    c.execute("SELECT DISTINCT place_id FROM review")
    place_ids = [row[0] for row in c.fetchall()]

    for pid in place_ids:
        # Obtenir info del lloc
        c.execute("SELECT name, address, locality, phone FROM review_text WHERE place_id = ?", (pid,))
        row = c.fetchone()
        if not row:
            continue
        name, address, locality, phone = row

        # Obtenir les ressenyes
        c.execute("SELECT author_name, rating, text, time FROM review WHERE place_id = ?", (pid,))
        reviews = [
            {"author": r[0], "rating": r[1], "text": r[2], "time": r[3]}
            for r in c.fetchall()
        ]

        data = {
            "place_id": pid,
            "name": name,
            "address": address,
            "locality": locality,
            "phone": phone,
            "reviews": reviews
        }

        filename = f"{OUTPUT_DIR}/{locality}_{name[:20].replace(' ', '_')}_{pid[:6]}.json".replace("/", "_")
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    conn.close()
    print(f"✅ {len(place_ids)} fitxers JSON creats a la carpeta '{OUTPUT_DIR}'")

if __name__ == "__main__":
    exportar_reviews()
