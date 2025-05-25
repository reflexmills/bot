import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

# Получаем значения
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище данных
active_dialogs = {}  # {user_id: admin_message_id}
message_pairs = {}   # {user_msg_id: admin_msg_id}

def get_admin_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для администратора"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✉ Ответить", callback_data=f"reply_{user_id}"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data=f"close_{user_id}")
    )
    return builder.as_markup()

@dp.message(Command("start", "help"))
async def start_handler(message: types.Message):
    """Обработка команд /start и /help"""
    await message.answer(
        "👋 Привет! Я бот для связи с администратором.\n\n"
        "Просто напишите ваш вопрос, и я перешлю его админу.\n"
        "Создан при поддержке @Luxxxll"
    )

@dp.message(F.chat.type == "private", ~F.from_user.id == ADMIN_ID)
async def user_message_handler(message: types.Message):
    """Обработка сообщений от пользователей"""
    try:
        user = message.from_user
        caption = f"👤 {user.full_name} (ID: {user.id}) пишет:\n\n"

        if message.text:
            sent = await bot.send_message(
                ADMIN_ID,
                caption + message.text,
                reply_markup=get_admin_keyboard(user.id)
            )
        elif message.photo:
            sent = await bot.send_photo(
                ADMIN_ID,
                message.photo[-1].file_id,
                caption=caption,
                reply_markup=get_admin_keyboard(user.id)
            )
        elif message.document:
            sent = await bot.send_document(
                ADMIN_ID,
                message.document.file_id,
                caption=caption,
                reply_markup=get_admin_keyboard(user.id)
            )
        else:
            return await message.answer("⚠️ Этот тип сообщения не поддерживается")

        # Сохраняем связь сообщений
        message_pairs[message.message_id] = sent.message_id
        active_dialogs[user.id] = sent.message_id
        await message.answer("✅ Ваше сообщение отправлено администратору")

    except Exception as e:
        logger.error(f"Ошибка пересылки: {e}")
        await message.answer("⚠️ Произошла ошибка при отправке сообщения")

@dp.message(F.chat.type == "private", F.from_user.id == ADMIN_ID, F.reply_to_message)
async def admin_reply_handler(message: types.Message):
    """Обработка ответов администратора через reply"""
    try:
        if not message.reply_to_message:
            return

        # Получаем ID пользователя из текста
        original_text = message.reply_to_message.text or message.reply_to_message.caption
        if not original_text or "ID: " not in original_text:
            return await message.answer("⚠️ Не удалось определить пользователя")

        user_id = int(original_text.split("ID: ")[1].split(")")[0])

        # Отправляем ответ
        if message.text:
            await bot.send_message(
                user_id,
                f"👨‍💻 Администратор отвечает:\n\n{message.text}"
            )
            await message.answer("✅ Ответ отправлен")
        
    except Exception as e:
        logger.error(f"Ошибка ответа: {e}")
        await message.answer("⚠️ Ошибка при отправке ответа")
@dp.callback_query(F.data.startswith("reply_"))
async def reply_callback_handler(callback: types.CallbackQuery):
    """Обработка кнопки 'Ответить'"""
    try:
        user_id = int(callback.data.split("_")[1])
        await callback.message.answer(
            f"Отправьте ответ пользователю {user_id}:",
            reply_markup=ForceReply(selective=True)
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка в reply_callback: {e}")

@dp.callback_query(F.data.startswith("close_"))
async def close_callback_handler(callback: types.CallbackQuery):
    """Обработка кнопки 'Закрыть'"""
    try:
        user_id = int(callback.data.split("_")[1])
        await bot.send_message(user_id, "❌ Диалог с администратором завершен")
        await callback.message.edit_text(f"Диалог с {user_id} закрыт")
        await callback.answer()
        
        # Удаляем из активных диалогов
        if user_id in active_dialogs:
            del active_dialogs[user_id]
    except Exception as e:
        logger.error(f"Ошибка в close_callback: {e}")

@dp.message(F.chat.type == "private")
async def fallback_handler(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        return
        
    # Если сообщение не команда /start и не обработано другими хендлерами
    if not message.text or not message.text.startswith('/'):
        await user_message_handler(message)  # Перенаправляем в основной обработчик
    else:
        await message.answer("ℹ️ Неизвестная команда. Используйте /start")
        
import asyncio
import logging

async def main():
    while True:  # Бесконечный цикл
        try:
            await dp.start_polling(bot, skip_updates=True)
        except Exception as e:
            logging.error(f"Ошибка: {e}. Перезапуск через 5 секунд...")
            await asyncio.sleep(5)  # Пауза перед перезапуском

if name == "main":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
