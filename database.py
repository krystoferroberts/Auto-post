
import sqlite3
import logging

logging.basicConfig(level=logging.INFO)

class Database:
    def get_all_ads(self):
        """ Получает все объявления из базы данных """
        self.cursor.execute("SELECT id, user_id, username, image, description, category, delivery, city, published FROM posts")
        ads = self.cursor.fetchall()
        return [{"id": ad[0], "user_id": ad[1], "username": ad[2], "image": ad[3], 
         "description": ad[4], "category": ad[5], "delivery": ad[6], "city": ad[7]} 
        for ad in ads]
        # Преобразуем результат в список словарей
        ad_list = []
        for ad in ads:
            ad_list.append({
            "id": ad[0],
            "user_id": ad[1],
            "username": ad[2],
            "image": ad[3],
            "description": ad[4],
            "category": ad[5],
            "delivery": ad[6],
            "city": ad[7],
            "published": ad[8]
        })
    
        return ad_list

    def __init__(self, db_path="ads.db"):
        """ Initializes the database connection """
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
    def create_tables(self):
        """ Создает таблицы, если они не существуют """
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            image TEXT DEFAULT '',
            description TEXT DEFAULT '',
            category TEXT DEFAULT '',
            delivery TEXT DEFAULT '',
            city TEXT DEFAULT '',
            published INTEGER DEFAULT 0,  -- Добавляем published для отметки отправки
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""")
    
        # Проверяем, есть ли колонка "published", если нет — добавляем
        self.cursor.execute("PRAGMA table_info(posts)")
        columns = [column[1] for column in self.cursor.fetchall()]
        if "published" not in columns:
            self.cursor.execute("ALTER TABLE posts ADD COLUMN published INTEGER DEFAULT 0")
            self.conn.commit()

        self.conn.commit()

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
        """)

        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY
        )
        """)

        # Ensure all required columns exist
        self.ensure_column("posts", "image", "TEXT DEFAULT ''")
        self.ensure_column("posts", "description", "TEXT DEFAULT ''")
        self.ensure_column("posts", "category", "TEXT DEFAULT ''")
        self.ensure_column("posts", "delivery", "TEXT DEFAULT ''")
        self.ensure_column("posts", "city", "TEXT DEFAULT ''")

        self.conn.commit()

    def ensure_column(self, table, column, col_type):
        """ Ensures that a specific column exists in a table """
        self.cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in self.cursor.fetchall()]
        if column not in columns:
            self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            self.conn.commit()

    def add_or_update_post(self, user_id, username, image, text, category, delivery, city):
        """ Добавляет или обновляет объявление пользователя """
        try:
            self.cursor.execute("""
            INSERT INTO posts (user_id, username, image, text, category, delivery, city)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) 
            DO UPDATE SET 
                username = excluded.username,
                image = excluded.image,
                text = excluded.text,
                category = excluded.category,
                delivery = excluded.delivery,
                city = excluded.city
            """, (user_id, username, image, text, category, delivery, city))
            
            self.conn.commit()
            logging.info(f"✅ Объявление сохранено для {user_id}")
        except sqlite3.Error as e:
            logging.error(f"❌ Ошибка при добавлении объявления: {e}")

    def get_all_posts(self):
        """ Retrieves all stored posts """
        self.cursor.execute("SELECT * FROM posts")
        return self.cursor.fetchall()

    def block_user(self, user_id):
        """ Blocks a user """
        self.cursor.execute("INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)", (user_id,))
        self.conn.commit()

    def unblock_user(self, user_id):
        """ Unblocks a user """
        self.cursor.execute("DELETE FROM banned_users WHERE user_id=?", (user_id,))
        self.conn.commit()

    def is_user_blocked(self, user_id):
        """ Checks if a user is blocked """
        self.cursor.execute("SELECT 1 FROM banned_users WHERE user_id=?", (user_id,))
        return self.cursor.fetchone() is not None

    def get_channels(self):
        """ Retrieves allowed channels """
        self.cursor.execute("SELECT id FROM channels")
        return [row[0] for row in self.cursor.fetchall()]
    def delete_old_ads(self):
        """ Удаляет объявления, которые были опубликованы более 30 дней назад """
        self.cursor.execute("DELETE FROM posts WHERE created_at <= datetime('now', '-30 days')")
        self.conn.commit()
    def add_or_update_post(self, user_id, username, image, description, category, delivery, city):
        """ Если пользователь уже отправил объявление, заменяем его новым """
        self.cursor.execute("DELETE FROM posts WHERE user_id=?", (user_id,))
        self.cursor.execute("""
        INSERT INTO posts (user_id, username, image, description, category, delivery, city, published, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id) DO UPDATE SET 
        username=excluded.username,
        image=excluded.image,
        description=excluded.description,
        category=excluded.category,
        delivery=excluded.delivery,
        city=excluded.city
        """, (user_id, username, image, description, category, delivery, city))
        self.conn.commit()

    def get_unpublished_ads(self):
        """ Получает только НЕОТПРАВЛЕННЫЕ объявления """
        self.cursor.execute("SELECT id, user_id, username, image, description, category, delivery, city FROM posts WHERE published = 0")
        ads = self.cursor.fetchall()
        return [{"id": ad[0], "user_id": ad[1], "username": ad[2], "image": ad[3], "description": ad[4], "category": ad[5], "delivery": ad[6], "city": ad[7]} for ad in ads]
    def mark_as_published(self, post_id):
        """ Помечает объявление как отправленное """
        self.cursor.execute("UPDATE posts SET published = 1 WHERE id = ?", (post_id,))
        self.conn.commit()
