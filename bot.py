import os
import random
import asyncio
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.utils import executor
from dotenv import load_dotenv

# Загрузка переменных из .env файла
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота и диспетчера
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Пример базы слов. Может быть расширена по вашему усмотрению.
word_database = {
    # ... (ваш словарь здесь)
}

# Пример структуры данных для отслеживания прогресса пользователей
user_progress = {}  # user_id: {"goal": int, "current_words": set, "learned_words": set}


@dp.message_handler(commands=["start"])
async def start(message: types.Message):
    user_id = message.from_user.id
    user_progress[user_id] = {"goal": 100,
                              "current_words": set(), "learned_words": set()}
    await message.answer("Привет! Давай начнем изучение слов. Отправь /learn для начала изучения.")


@dp.message_handler(commands=["learn"])
async def learn(message: types.Message):
    await send_word_to_user(message.from_user.id)


@dp.message_handler(commands=["test"])
async def test(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_progress:
        words_to_test = user_progress[user_id]["current_words"]
        if words_to_test:
            await message.answer("Тест: переведите слова на английский.")
            for word in words_to_test:
                await message.answer(f"Переведите: {word_database[word]}")
        else:
            await message.answer("Пока нет слов для тестирования.")
    else:
        await message.answer("Для начала начните изучение с /start")


@dp.message_handler(commands=["progress"])
async def progress(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_progress:
        current_progress = len(user_progress[user_id]["learned_words"])
        goal = user_progress[user_id]["goal"]
        await message.answer(f"Ваш прогресс: {current_progress}/{goal} слов")
    else:
        await message.answer("Для начала начните изучение с /start")


@dp.message_handler(commands=["learned"])
async def learned(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_progress:
        learned_words = user_progress[user_id]["learned_words"]
        if learned_words:
            words_text = "\n".join(
                [f"{word} - {word_database[word]}" for word in learned_words])
            await message.answer(f"Вы выучили следующие слова:\n{words_text}")
        else:
            await message.answer("Пока вы не выучили ни одного слова.")
    else:
        await message.answer("Для начала начните изучение с /start")


async def send_word_to_user(user_id):
    if user_id in user_progress:
        now = datetime.datetime.now()
        current_day = now.day
        current_hour = now.hour

        # Определяем номер недели в году
        week_number = now.isocalendar()[1]

        # Если началась новая неделя, сбрасываем текущие слова пользователя
        if "current_week" not in user_progress[user_id] or user_progress[user_id]["current_week"] < week_number:
            user_progress[user_id]["current_words"] = set()
            user_progress[user_id]["current_week"] = week_number

        # Определяем время отправки уведомлений
        notification_hours = [10, 15, 20]  # Например, утро, день и вечер

        for hour in notification_hours:
            if current_hour < hour:
                # Вычисляем время до следующего уведомления
                time_to_wait = datetime.datetime(
                    now.year, now.month, now.day, hour) - now
                await asyncio.sleep(time_to_wait.seconds)

                words_to_learn = list(word_database.keys())
                random.shuffle(words_to_learn)

                # Исключаем уже выученные слова
                words_to_learn = [
                    word for word in words_to_learn if word not in user_progress[user_id]["learned_words"]]

                # Отправляем 3 слова в уведомлении
                words_to_learn = words_to_learn[:3]
                user_progress[user_id]["current_words"].update(words_to_learn)
                words_text = "\n".join(
                    [f"{word} - {word_database[word]}" for word in words_to_learn])
                await bot.send_message(user_id, f"Изучай следующие слова:\n{words_text}")

        # Если текущий день - последний день недели (например, воскресенье), предлагаем пройти тест
        if now.weekday() == 6:
            await bot.send_message(user_id, "Неделя подошла к концу. Чтобы проверить свои знания, используйте /test")


@dp.message_handler(lambda message: message.text.lower() in ["пропустить", "skip"])
async def skip_word(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_progress:
        current_words = user_progress[user_id]["current_words"]
        if current_words:
            word_to_skip = current_words.pop()
            await send_word_to_user(user_id)
            await bot.send_message(user_id, f"Слово '{word_database[word_to_skip]}' пропущено. Продолжайте изучение.")
        else:
            await bot.send_message(user_id, "Пока нет слов для пропуска.")
    else:
        await bot.send_message(user_id, "Для начала начните изучение с /start")


@dp.message_handler(lambda message: message.text.lower() in ["выучено", "learned"])
async def word_learned(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_progress:
        current_words = user_progress[user_id]["current_words"]
        if current_words:
            word_learned = current_words.pop()
            user_progress[user_id]["learned_words"].add(word_learned)
            await bot.send_message(user_id, f"Слово '{word_database[word_learned]}' отмечено как выученное. Продолжайте изучение.")
            await send_word_to_user(user_id)
        else:
            await bot.send_message(user_id, "Пока нет слов для отметки как выученные.")
    else:
        await bot.send_message(user_id, "Для начала начните изучение с /start")


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
