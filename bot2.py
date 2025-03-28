import asyncio
import os
import json
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.enums import ChatType
from aiogram.client.session.aiohttp import AiohttpSession
from config import TOKEN, CHANNEL_ID, ADMIN_IDS

# Создаем объект бота
session = AiohttpSession()
bot = Bot(token=TOKEN, parse_mode=None, session=session)

# Создаем Dispatcher (БЕЗ АРГУМЕНТА bot)
dp = Dispatcher()

# Папка для хранения постов
POSTS_DIR = "posts"
os.makedirs(POSTS_DIR, exist_ok=True)

# Файл для забаненных пользователей
BANNED_USERS_FILE = "banned_users.json"
if not os.path.exists(BANNED_USERS_FILE):
    with open(BANNED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

# Словарь для хранения ID всех сообщений в каждом чате
chat_message_ids = {}

# Функции для работы с банами
def load_banned_users():
    with open(BANNED_USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_banned_users(users):
    with open(BANNED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False)

# Игнорируем сообщения в группах и каналах
@dp.message(F.chat.type.in_([ChatType.GROUP, ChatType.SUPERGROUP, ChatType.CHANNEL]))
async def ignore_group_messages(message: Message):
    return

# Прием постов только в личных сообщениях (текст и фото)
@dp.message(F.chat.type == ChatType.PRIVATE, F.content_type.in_([types.ContentType.TEXT, types.ContentType.PHOTO]))
async def receive_post(message: Message):
    user_id = message.from_user.id

    # Проверяем бан
    banned_users = load_banned_users()
    if user_id in banned_users:
        await message.reply("⛔ Вы заблокированы и не можете отправлять посты.")
        return

    user_file = os.path.join(POSTS_DIR, f"{user_id}.json")
    post_data = {
        "text": message.caption if message.photo else message.text,
        "photo": message.photo[-1].file_id if message.photo else None,
        "time": datetime.now().isoformat()
    }

    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False)

    await message.reply("✅ Ваш пост сохранен и будет опубликован в ближайшее время.")

# Публикация постов раз в 2 часа
async def post_scheduler():
    while True:
        try:
            # Удаляем все предыдущие сообщения бота в каждом чате
            for chat_id in CHANNEL_ID:
                if chat_id in chat_message_ids:
                    for message_id in chat_message_ids[chat_id]:
                        try:
                            await bot.delete_message(chat_id, message_id)
                        except TelegramBadRequest as e:
                            print(f"⚠️ Не удалось удалить сообщение в {chat_id}: {e}")
                    chat_message_ids[chat_id] = []  # Очищаем список сообщений

            # Публикуем все посты
            for filename in os.listdir(POSTS_DIR):
                file_path = os.path.join(POSTS_DIR, filename)

                with open(file_path, "r", encoding="utf-8") as f:
                    post_data = json.load(f)

                # Отправляем пост во все каналы/группы
                for chat_id in CHANNEL_ID:
                    try:
                        if post_data["photo"]:
                            sent_message = await bot.send_photo(chat_id, post_data["photo"], caption=post_data["text"])
                        else:
                            sent_message = await bot.send_message(chat_id, post_data["text"])

                        # Сохраняем ID нового сообщения
                        if chat_id not in chat_message_ids:
                            chat_message_ids[chat_id] = []
                        chat_message_ids[chat_id].append(sent_message.message_id)

                    except TelegramBadRequest:
                        print(f"⚠️ Бот не может отправить сообщение в {chat_id}. Возможно, он удален из группы/канала.")

            await asyncio.sleep(43200)  # Ждем 2 часа перед следующей отправкой
        except Exception as e:
            print(f"Ошибка в post_scheduler: {e}")

# Команда /ban <user_id> - бан пользователя
@dp.message(Command("ban"))
async def ban_user(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.split()[1])
        banned_users = load_banned_users()
        if user_id not in banned_users:
            banned_users.append(user_id)
            save_banned_users(banned_users)
            await message.reply(f"✅ Пользователь {user_id} заблокирован.")
        else:
            await message.reply("⚠️ Пользователь уже в бане.")
    except:
        await message.reply("❌ Ошибка! Используйте: /ban <user_id>")

# Команда /unban <user_id> - разбан пользователя
@dp.message(Command("unban"))
async def unban_user(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        user_id = int(message.text.split()[1])
        banned_users = load_banned_users()
        if user_id in banned_users:
            banned_users.remove(user_id)
            save_banned_users(banned_users)
            await message.reply(f"✅ Пользователь {user_id} разбанен.")
        else:
            await message.reply("⚠️ Пользователь не был в бане.")
    except:
        await message.reply("❌ Ошибка! Используйте: /unban <user_id>")

# Команда /all_posts - просмотр всех постов
@dp.message(Command("all_posts"))
async def all_posts(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    posts_text = []
    for filename in os.listdir(POSTS_DIR):
        user_id = filename.replace(".json", "")
        with open(os.path.join(POSTS_DIR, filename), "r", encoding="utf-8") as f:
            post_data = json.load(f)
            posts_text.append(f"👤 User ID: {user_id}\n📜 Post: {post_data['text']}\n")

    if posts_text:
        await message.reply("\n".join(posts_text))
    else:
        await message.reply("🔍 Постов пока нет.")

# Запуск бота
async def main():
    asyncio.create_task(post_scheduler())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())