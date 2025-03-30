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

# Инициализация объектов
session = AiohttpSession()
bot = Bot(token=TOKEN, session=session)
dp = Dispatcher()

# Конфигурация
POSTS_DIR = "posts"
BAN_LIST_FILE = "banned_users.json"
os.makedirs(POSTS_DIR, exist_ok=True)

def load_banned_users():
    try:
        with open(BAN_LIST_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_banned_users(banned_users):
    with open(BAN_LIST_FILE, "w") as f:
        json.dump(banned_users, f)

@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("👋 Отправь мне пост (текст или фото с подписью)")

@dp.message(Command("ban"), F.from_user.id.in_(ADMIN_IDS))
async def ban_user(message: Message):
    try:
        user_id = int(message.text.split()[1])
        banned_users = load_banned_users()
        if user_id not in banned_users:
            banned_users.append(user_id)
            save_banned_users(banned_users)
            await message.answer(f"🚫 Пользователь {user_id} забанен")
    except (IndexError, ValueError):
        await message.answer("❌ Используй: /ban <user_id>")

@dp.message(Command("unban"), F.from_user.id.in_(ADMIN_IDS))
async def unban_user(message: Message):
    try:
        user_id = int(message.text.split()[1])
        banned_users = load_banned_users()
        if user_id in banned_users:
            banned_users.remove(user_id)
            save_banned_users(banned_users)
            await message.answer(f"✅ Пользователь {user_id} разбанен")
    except (IndexError, ValueError):
        await message.answer("❌ Используй: /unban <user_id>")

@dp.message(F.chat.type == ChatType.PRIVATE, F.content_type.in_({'text', 'photo'}))
async def receive_post(message: Message):
    user_id = message.from_user.id
    banned_users = load_banned_users()
    
    if user_id in banned_users and message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У тебя нет прав для отправки постов.")
        return

    post_data = {
        "text": message.caption if message.photo else message.text,
        "photo": message.photo[-1].file_id if message.photo else None,
        "time": datetime.now().isoformat()
    }
    
    user_file = os.path.join(POSTS_DIR, f"{user_id}.json")
    with open(user_file, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False)
    
    await message.reply("✅ Ваш пост сохранен и будет опубликован в ближайшее время.")

async def post_scheduler():
    while True:
        now = datetime.now()
        for filename in os.listdir(POSTS_DIR):
            if filename.endswith(".json"):
                file_path = os.path.join(POSTS_DIR, filename)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        post_data = json.load(f)
                    
                    post_time = datetime.fromisoformat(post_data["time"])
                    if now - post_time >= timedelta(hours=2):
                        user_id = int(filename.split(".")[0])
                        banned_users = load_banned_users()
                        
                        if user_id not in banned_users:
                            for chat_id in CHANNEL_ID:
                                try:
                                    if post_data["photo"]:
                                        await bot.send_photo(
                                            chat_id=chat_id,
                                            photo=post_data["photo"],
                                            caption=post_data["text"]
                                        )
                                    else:
                                        await bot.send_message(
                                            chat_id=chat_id,
                                            text=post_data["text"]
                                        )
                                    os.remove(file_path)
                                except TelegramBadRequest as e:
                                    print(f"Ошибка отправки в чат {chat_id}: {e}")
                except Exception as e:
                    print(f"Ошибка обработки файла {filename}: {str(e)}")
        
        await asyncio.sleep(60)

async def main():
    await asyncio.gather(
        dp.start_polling(bot),
        post_scheduler()
    )

if __name__ == "__main__":
    asyncio.run(main())
