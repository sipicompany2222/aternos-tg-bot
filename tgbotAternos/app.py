import os
import logging
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLoggerт(__name__)

# --- Конфигурация ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден!")

BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://aternos-tg-bot-8n19.onrender.com")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Обработчики команд ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"✅ Получена команда /start от {message.from_user.id}")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🚀 Запустить сервер")]],
        resize_keyboard=True
    )
    await message.answer("Привет! Нажми кнопку, чтобы запустить Minecraft сервер на Aternos.", reply_markup=keyboard)

@dp.message()
async def echo_all(message: types.Message):
    logger.info(f"📩 Получено сообщение: {message.text} от {message.from_user.id}")
    await message.answer(f"✅ Бот работает! Вы написали: {message.text}")

# --- Flask приложение ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running with Webhook!"

@app.route("/health")
def health():
    return "OK"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    """Telegram отправляет обновления сюда (синхронная версия)"""
    try:
        # Получаем данные от Telegram
        update_data = request.get_json()
        logger.info(f"📨 Получено обновление от Telegram")
        
        # Создаём объект Update и обрабатываем его
        update = types.Update(**update_data)
        
        # Синхронная обработка: запускаем обработчики вручную
        import asyncio
        async def process_update():
            await dp.feed_update(bot, update)
        
        # Запускаем асинхронную обработку в синхронном контексте
        asyncio.run(process_update())
        
        return "OK", 200
    except Exception as e:
        logger.error(f"❌ Ошибка в webhook: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return "Error", 500

@app.route("/set_webhook")
def set_webhook():
    """Вручную установить вебхук"""
    try:
        import asyncio
        async def set():
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
            return f"✅ Webhook установлен на {WEBHOOK_URL}"
        
        result = asyncio.run(set())
        logger.info(result)
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка установки webhook: {e}")
        return f"❌ Ошибка: {e}"

@app.route("/remove_webhook")
def remove_webhook():
    """Удалить вебхук (для отладки)"""
    try:
        import asyncio
        async def remove():
            await bot.delete_webhook(drop_pending_updates=True)
            return "✅ Webhook удалён"
        
        result = asyncio.run(remove())
        logger.info(result)
        return result
    except Exception as e:
        return f"❌ Ошибка: {e}"

# --- Запуск ---
if __name__ == "__main__":
    logger.info(f"🚀 Запуск бота с webhook: {WEBHOOK_URL}")
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
