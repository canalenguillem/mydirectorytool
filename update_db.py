import sqlite3

DB_PATH = "places.db"

def eliminar_taula_review_text():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS review_text")
    conn.commit()
    conn.close()
    print("✅ Taula 'review_text' eliminada correctament.")

if __name__ == "__main__":
    eliminar_taula_review_text()
