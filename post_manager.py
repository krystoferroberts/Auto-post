import logging
from aiogram import Bot
from database import Database

logging.basicConfig(level=logging.INFO)

db = Database()

async def publish_posts(bot: Bot):
    """ Отправляет посты во все подключенные каналы """
    try:
        posts = db.get_unpublished_ads()
        channels = db.get_channels()  # Получаем список ID каналов

        logging.info(f"📩 Начинаю отправку постов...")
        
        if not posts:
            logging.info("⚠ Нет постов для отправки.")
            return
        
        if not channels:
            logging.info("⚠ Нет подключенных каналов.")
            return
        
        for channel_id in channels:
            logging.info(f"📩 Отправка объявлений в {channel_id}...")

            for post in posts:
                user_id, username, image, text = post[1:]

                # Проверяем, не заблокирован ли пользователь
                if db.is_user_blocked(user_id):
                    logging.info(f"🚫 Пользователь {user_id} заблокирован, пост не отправлен.")
                    continue
                
                try:
                    username, image, description, category, delivery, city = post[1:]
                    message_text = f"👤 {username}\n📜 {description}\n🏷 {category} {delivery} {city}"

                    
                    if image:
                        await bot.send_photo(chat_id=channel_id, photo=image, caption=message_text)
                    else:
                        await bot.send_message(chat_id=channel_id, text=message_text)

                    logging.info(f"✅ Пост отправлен в {channel_id}")
                except Exception as e:
                    logging.error(f"⚠ Ошибка отправки в {channel_id}: {e}")
    except Exception as e:
        logging.error(f"❌ Ошибка в publish_posts: {e}")
    except Exception as e:
        logging.error(f"❌ Ошибка в publish_posts: {e}")
