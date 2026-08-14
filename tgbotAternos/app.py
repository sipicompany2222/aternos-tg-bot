import os
import asyncio
import threading
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- Конфигурация ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден!")

BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://aternos-tg-bot-8n19.onrender.com")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создаём цикл событий для всего приложения
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# --- Обработчики команд ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    print(f"✅ Получена команда /start от {message.from_user.id}")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🚀 Запустить сервер")]],
        resize_keyboard=True
    )
    await message.answer("Привет! Нажми кнопку, чтобы запустить Minecraft сервер на Aternos.", reply_markup=keyboard)

@dp.message()
async def echo_all(message: types.Message):
    print(f"📩 Получено сообщение: {message.text} от {message.from_user.id}")
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
    """Telegram отправляет обновления сюда"""
    try:
        update_data = request.get_json()
        print(f"📨 Получено обновление от Telegram")
        
        update = types.Update(**update_data)
        
        # Используем существующий цикл событий
        future = asyncio.run_coroutine_threadsafe(
            dp.feed_update(bot, update),
            loop
        )
        future.result(timeout=30)  # Ждём результат не более 30 секунд
        
        return "OK", 200
    except Exception as e:
        print(f"❌ Ошибка в webhook: {e}")
        import traceback
        print(traceback.format_exc())
        return "Error", 500

@app.route("/set_webhook")
def set_webhook():
    """Вручную установить вебхук"""
    try:
        async def set():
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
            return f"✅ Webhook установлен на {WEBHOOK_URL}"
        
        # Используем существующий цикл
        future = asyncio.run_coroutine_threadsafe(set(), loop)
        result = future.result(timeout=30)
        print(result)
        return result
    except Exception as e:
        print(f"❌ Ошибка установки webhook: {e}")
        return f"❌ Ошибка: {e}"

@app.route("/remove_webhook")
def remove_webhook():
    """Удалить вебхук (для отладки)"""
    try:
        async def remove():
            await bot.delete_webhook(drop_pending_updates=True)
            return "✅ Webhook удалён"
        
        future = asyncio.run_coroutine_threadsafe(remove(), loop)
        result = future.result(timeout=30)
        print(result)
        return result
    except Exception as e:
        return f"❌ Ошибка: {e}"

# --- Запуск ---
if __name__ == "__main__":
    print(f"🚀 Запуск бота с webhook: {WEBHOOK_URL}")
    
    # Запускаем цикл событий в фоновом потоке
    def run_loop():
        loop.run_forever()
    
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
