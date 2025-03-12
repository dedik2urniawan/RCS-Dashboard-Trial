import sqlite3

def create_user_table():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('admin_dinkes', 'admin_puskesmas', 'stakeholder')) NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Tabel user berhasil dibuat!")

def create_admin_user():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Tambahkan user default jika belum ada
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("admin_dinkes", "admin123", "admin_dinkes"))
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("admin_puskesmas", "puskesmas123", "admin_puskesmas"))
    cursor.execute("INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
                   ("stakeholder", "stakeholder123", "stakeholder"))

    conn.commit()
    conn.close()
    print("✅ User default berhasil ditambahkan!")

if __name__ == "__main__":
    create_user_table()
    create_admin_user()
    print("✅ Database user berhasil dibuat & diisi!")
