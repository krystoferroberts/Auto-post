import asyncio
import post_manager
from aiogram import Bot
from config1 import TOKEN

bot = Bot(token=TOKEN)

async def scheduled_task():
    """ Функция автоматической публикации каждые 2 часа """
    while True:
        print("🔄 Рассылка запущена! Сейчас вызываю publish_posts()")
        await post_manager.publish_posts(bot)
        print("🔄 Рассылка запущена!")
        await asyncio.sleep(600)  # 2 часа
