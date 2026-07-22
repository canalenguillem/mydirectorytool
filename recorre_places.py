import sqlite3
import requests
from decouple import config

DB_PATH = "places.db"
WP_URL = config("WP_URL")
AUTH = (config("WP_USER"), config("WP_APP_PASS"))

# Connectar a la base de dades
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Obtenir tots els place_id i noms locals
c.execute("SELECT place_id, name FROM place")
local_places = {row[0]: row[1] for row in c.fetchall()}
print(f"Trobats {len(local_places)} restaurants a la base de dades")

# Obtenir tots els posts des de WordPress (paginat)
wp_place_ids = set()
page = 1
while True:
    r = requests.get(f"{WP_URL}/wp-json/wp/v2/restaurante?per_page=100&page={page}", auth=AUTH)
    if r.status_code != 200:
        print(f"[ERROR] Error recuperant pàgina {page}: {r.status_code}")
        break

    posts = r.json()
    if not posts:
        break  # No més posts

    for post in posts:
        acf_fields = post.get("acf", {})
        place_id = acf_fields.get("place_id")
        if place_id:
            wp_place_ids.add(place_id)

    page += 1

print(f"Trobats {len(wp_place_ids)} place_id a WordPress")

# Comparar i mostrar amb noms
missing_in_wp = [(pid, local_places[pid]) for pid in local_places if pid not in wp_place_ids]

print(f"\n>>> {len(missing_in_wp)} restaurants sense entrada a WordPress:")
for pid, name in missing_in_wp:
    print(f"- {name} ({pid})")

conn.close()
