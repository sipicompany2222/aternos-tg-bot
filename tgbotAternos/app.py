import os
import asyncio
import threading
from flask import Flask
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aternos_api import AternosAPI

# --- Конфигурация ---
BOT_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден!")

ATERNOS_LOGIN = os.environ.get("ATERNOS_LOGIN")
ATERNOS_PASS = os.environ.get("ATERNOS_PASS")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Глобальная переменная для хранения сессии Aternos
aternos_session = None

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
    global aternos_session
    
    if not ATERNOS_LOGIN or not ATERNOS_PASS:
        await message.answer("⚠️ Ошибка: логин или пароль от Aternos не настроены.")
        return

    await message.answer("🔄 Подключаюсь к Aternos...")

    try:
        # Создаём сессию, если её нет
        if aternos_session is None:
            aternos_session = AternosAPI(ATERNOS_LOGIN, ATERNOS_PASS)
            
        # Логинимся
        if not aternos_session.authenticated:
            if not aternos_session.login():
                await message.answer("❌ Не удалось войти в Aternos. Проверьте логин и пароль.")
                return
        
        # Получаем серверы
        servers = aternos_session.get_servers()
        if not servers:
            await message.answer("❌ У вас нет серверов на этом аккаунте Aternos.")
            return
        
        # Берём первый сервер
        server = servers[0]
        server_id = server.get("id")
        server_name = server.get("name", "Без названия")
        
        await message.answer(f"🔄 Запускаю сервер '{server_name}'...")
        
        # Запускаем
        if aternos_session.start_server(server_id):
            await message.answer(f"✅ Сервер '{server_name}' запускается! Статус: {aternos_session.get_server_status(server_id)}")
        else:
            await message.answer(f"❌ Не удалось запустить сервер. Возможно, он уже запущен.")
            
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")

# --- Flask для Render ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running!"

@app.route('/health')
def health():
    return "OK"

# --- Запуск бота ---
def run_bot():
    asyncio.run(dp.start_polling(bot))

if name == 'main':
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
