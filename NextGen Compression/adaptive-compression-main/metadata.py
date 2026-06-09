import sqlite3
import os
import time

class CompressionDB:
    def __init__(self, db_path="data/project_history.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    filename TEXT,
                    original_size INTEGER,
                    compressed_size INTEGER,
                    entropy REAL,
                    engine TEXT,
                    duration REAL,
                    ratio REAL,
                    eco_mode INTEGER
                )
            """)

    def log_run(self, filename, orig_size, comp_size, entropy, engine, duration, eco_mode):
        ratio = (comp_size / orig_size) if orig_size > 0 else 1.0
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO history (filename, original_size, compressed_size, entropy, engine, duration, ratio, eco_mode)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (filename, orig_size, comp_size, entropy, engine, duration, ratio, 1 if eco_mode else 0))

    def get_stats(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*), AVG(ratio), AVG(duration) FROM history")
            return cursor.fetchone()

    def get_recent_runs(self, limit=10):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT engine, ratio, duration FROM history ORDER BY timestamp DESC LIMIT ?", (limit,))
            return cursor.fetchall()