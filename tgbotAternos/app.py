import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from python_aternos import Client

# --- Конфигурация ---
BOT_TOKEN = os.environ.get("8728302550:AAGhnxJL5LsHUqFApsNNrsRdnx7Vgs5u3dw")
if not BOT_TOKEN:
    raise ValueError("Переменная окружения TELEGRAM_TOKEN не найдена!")
login = "Sipicompany"
password = "Sipicompany2222"

# Данные Aternos лучше тоже хранить в переменных окружения на Render
ATERNOS_LOGIN = os.environ.get("login")
ATERNOS_PASS = os.environ.get("password")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- Обработчики команд ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🚀 Запустить сервер")]],
        resize_keyboard=True
    )
    await message.answer("Привет! Нажми кнопку, чтобы запустить Minecraft сервер на Aternos.", reply_markup=keyboard)

@dp.message(lambda message: message.text == "🚀 Запустить сервер")
async def start_server(message: types.Message):
    if not ATERNOS_LOGIN or not ATERNOS_PASS:
        await message.answer("⚠️ Ошибка: логин или пароль от Aternos не настроены.")
        return

    await message.answer("🔄 Пытаюсь запустить сервер... Это может занять минуту.")

    try:
        # Асинхронный запуск, чтобы не блокировать бота
        aternos = Client.from_credentials(ATERNOS_LOGIN, ATERNOS_PASS)
        servers = aternos.list_servers()
        if not servers:
            await message.answer("❌ У вас нет серверов на этом аккаунте Aternos.")
            return
        server = servers[0]
        server.start()
        await message.answer(f"✅ Сервер '{server.domain}' запускается! Статус: {server.status}")
    except Exception as e:
        await message.answer(f"❌ Произошла ошибка при запуске: {str(e)}")

# --- Flask для Render ---
app = Flask(name)

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

# --- Запуск бота в фоновом потоке (для polling) ---
def run_bot():
    asyncio.run(dp.start_polling(bot))

if name == 'main':
    # Запускаем бота в отдельном потоке
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Запускаем Flask сервер
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
