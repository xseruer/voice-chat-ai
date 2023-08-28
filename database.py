import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_name="./data/sqlite.db"):
        self.conn = sqlite3.connect(db_name)
        self.create_table()

    def create_table(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_time DATETIME,
                text TEXT,
                path TEXT,
                type TEXT
            );''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_time DATETIME,
                session TEXT,
                role TEXT,
                content TEXT
            );''')
        self.conn.commit()

    def insert_chat(self, session: str, role: str, content: str):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO chat(created_time, session, role, content) VALUES (?, ?, ?, ?)",
                       (now, session, role, content))
        self.conn.commit()
    
    def insert_audio(self, text:str, path:str, type:str):
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO audio(created_time, text, path, type) VALUES (?, ?, ?, ?)",
                       (now, text, path, type))
        self.conn.commit()

    def get_tts_cache(self,text):
        cursor = self.conn.cursor()
        query_string = "SELECT path FROM audio WHERE type = 'tts' and text = ? ORDER BY created_time DESC LIMIT 1"
        cursor.execute(query_string, (text,))
        res = cursor.fetchone()
        return res[0] if res else None

if __name__ == "__main__":
    db = Database()
    db.get_asr_cache('我在你说')
