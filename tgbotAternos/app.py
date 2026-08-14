import os
import asyncio
import threading
import requests
import re
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# --- Конфигурация ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_TOKEN не найден!")

ATERNOS_LOGIN = os.environ.get("ATERNOS_LOGIN")
ATERNOS_PASS = os.environ.get("ATERNOS_PASS")

BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://aternos-tg-bot-8n19.onrender.com")
WEBHOOK_PATH = f"/webhook/{TOKEN}"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Создаём цикл событий для всего приложения
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# --- КЛАСС ATERNOS (ПРОСТЕЙШАЯ ВЕРСИЯ) ---
class AternosClient:
    def init(self, login, password):
        print(f"🔧 init вызван с login={login}")
        self.login = login
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.authenticated = False
        
    def login(self):
        try:
            print("🔐 Вход в Aternos...")
            resp = self.session.get('https://aternos.org/go/')
            csrf_match = re.search(r'name="csrf_token".*?value="(.*?)"', resp.text)
            csrf_token = csrf_match.group(1) if csrf_match else ''
            
            data = {
                'user': self.login,
                'password': self.password,
                'csrf_token': csrf_token
            }
            resp = self.session.post('https://aternos.org/login/', data=data)
            
            if 'dashboard' in resp.url or 'panel' in resp.url:
                self.authenticated = True
                print("✅ Вход выполнен!")
                return True
            print("❌ Ошибка входа")
            return False
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def get_servers(self):
        if not self.authenticated:
            return []
        try:
            resp = self.session.get('https://aternos.org/panel/ajax/servers/')
            return resp.json().get('servers', [])
        except:
            return []
    
    def start_server(self, server_id):
        if not self.authenticated:
            return False
        try:
            resp = self.session.get(f'https://aternos.org/panel/ajax/start/{server_id}/')
            return resp.status_code == 200
        except:
            return False

# Глобальный клиент
aternos_client = None

# --- ОБРАБОТЧИКИ ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🚀 Запустить сервер")]],
        resize_keyboard=True
    )
    await message.answer("Привет! Нажми кнопку, чтобы запустить Minecraft сервер.", reply_markup=keyboard)

@dp.message(lambda message: message.text == "🚀 Запустить сервер")
async def start_server(message: types.Message):
    global aternos_client
    
    if not ATERNOS_LOGIN or not ATERNOS_PASS:
        await message.answer("⚠️ Логин или пароль не настроены!")
        return

    await message.answer("🔄 Подключаюсь к Aternos...")

    try:
        # СОЗДАЁМ КЛИЕНТ ЗАНОВО КАЖДЫЙ РАЗ
        print("📦 Создаю НОВЫЙ клиент Aternos...")
        aternos_client = AternosClient(ATERNOS_LOGIN, ATERNOS_PASS)
        
        await message.answer("🔐 Вхожу в Aternos...")
        if not aternos_client.login():
            await message.answer("❌ Не удалось войти! Проверьте логин/пароль.")
            return
        
        await message.answer("📋 Получаю список серверов...")
        servers = aternos_client.get_servers()
        if not servers:
            await message.answer("❌ Нет серверов на аккаунте.")
            return
        
        server = servers[0]
        server_id = server.get('id')
        server_name = server.get('name', 'Без названия')
        
        await message.answer(f"🔄 Запускаю '{server_name}'...")
        
        if aternos_client.start_server(server_id):
            await message.answer(f"✅ Сервер '{server_name}' запускается!")
        else:
            await message.answer("❌ Не удалось запустить. Возможно, уже запущен.")
            
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        print(traceback.format_exc())
        await message.answer(f"❌ Ошибка: {str(e)}")

@dp.message()
async def echo(message: types.Message):
    await message.answer(f"Вы написали: {message.text}")

# --- FLASK ---
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot is running!"

@app.route("/health")
def health():
    return "OK"

@app.route("/debug")
def debug():
    global aternos_client
    return f"Клиент: {'создан' if aternos_client else 'НЕ создан'} | Авторизован: {aternos_client.authenticated if aternos_client else 'N/A'}"

@app.route(WEBHOOK_PATH, methods=["POST"])
def webhook():
    try:
        update_data = request.get_json()
        update = types.Update(**update_data)
        future = asyncio.run_coroutine_threadsafe(dp.feed_update(bot, update), loop)
        future.result(timeout=30)
        return "OK", 200
    except Exception as e:
        print(f"❌ Webhook ошибка: {e}")
        return "Error", 500

@app.route("/set_webhook")
def set_webhook():
    try:
        async def set():
            await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
            return f"✅ Webhook установлен"
        future = asyncio.run_coroutine_threadsafe(set(), loop)
        return future.result(timeout=30)
    except Exception as e:
        return f"❌ Ошибка: {e}"

# --- ЗАПУСК ---
if __name__ == "__main__":
    print(f"🚀 Бот запущен!")
    print(f"🔑 Aternos логин: {'✅' if ATERNOS_LOGIN else '❌'}")
    print(f"🔑 Aternos пароль: {'✅' if ATERNOS_PASS else '❌'}")
    
    def run_loop():
        loop.run_forever()
    
    threading.Thread(target=run_loop, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
