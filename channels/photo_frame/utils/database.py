import sqlite3
from pathlib import Path
from typing import Dict, Any, Optional, List

class PhotoFrameDB:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT UNIQUE NOT NULL,
            original_name TEXT NOT NULL,
            title TEXT DEFAULT '',
            description TEXT DEFAULT '',
            width INTEGER NOT NULL,
            height INTEGER NOT NULL,
            enabled BOOLEAN DEFAULT TRUE,
            sort_order INTEGER DEFAULT 0,
            times_shown INTEGER DEFAULT 0,
            last_shown_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            crop_x REAL DEFAULT 0.0,
            crop_y REAL DEFAULT 0.0,
            crop_width REAL DEFAULT 100.0,
            crop_height REAL DEFAULT 100.0,
            preserve_aspect_ratio BOOLEAN DEFAULT FALSE
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS channel_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()

    def add_image(self, image_data: Dict[str, Any]) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''INSERT INTO images (filename, original_name, width, height, enabled)
            VALUES (?, ?, ?, ?, ?)''',
            (image_data["filename"], image_data["original_name"], image_data["width"], image_data["height"], True))
        conn.commit()
        image_id = c.lastrowid
        conn.close()
        return image_id

    def get_image(self, image_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM images WHERE id=?', (image_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return dict(zip([d[0] for d in c.description], row))
        return None

    def get_all_images(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM images')
        rows = c.fetchall()
        conn.close()
        return [dict(zip([d[0] for d in c.description], row)) for row in rows]

    def get_enabled_images(self) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT * FROM images WHERE enabled=1')
        rows = c.fetchall()
        conn.close()
        return [dict(zip([d[0] for d in c.description], row)) for row in rows]

    def update_image(self, image_id: int, updates: Dict[str, Any]) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        fields = ', '.join([f'{k}=?' for k in updates.keys()])
        values = list(updates.values()) + [image_id]
        c.execute(f'UPDATE images SET {fields} WHERE id=?', values)
        conn.commit()
        success = c.rowcount > 0
        conn.close()
        return success

    def delete_image(self, image_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM images WHERE id=?', (image_id,))
        conn.commit()
        success = c.rowcount > 0
        conn.close()
        return success

    def toggle_image_enabled(self, image_id: int) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('UPDATE images SET enabled = NOT enabled WHERE id=?', (image_id,))
        conn.commit()
        success = c.rowcount > 0
        conn.close()
        return success

    def get_image_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM images')
        count = c.fetchone()[0]
        conn.close()
        return count

    def get_enabled_image_count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM images WHERE enabled=1')
        count = c.fetchone()[0]
        conn.close()
        return count

    def check_health(self) -> bool:
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute('SELECT 1')
            conn.close()
            return True
        except Exception:
            return False

    def get_settings(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT key, value FROM channel_settings')
        rows = c.fetchall()
        conn.close()
        settings = {}
        for k, v in rows:
            # Try to parse JSON values, fallback to string
            try:
                if v.lower() in ('true', 'false'):
                    settings[k] = v.lower() == 'true'
                elif v.isdigit():
                    settings[k] = int(v)
                else:
                    settings[k] = v
            except:
                settings[k] = v
        return settings

    def update_settings(self, settings: Dict[str, Any]):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        for k, v in settings.items():
            c.execute('REPLACE INTO channel_settings (key, value) VALUES (?, ?)', (k, str(v)))
        conn.commit()
        conn.close()
