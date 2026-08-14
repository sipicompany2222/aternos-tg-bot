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

# --- Класс для работы с Aternos (ИСПРАВЛЕННЫЙ) ---
class AternosClient:
    def init(self, login, password):  # ← Теперь правильно принимает аргументы!
        self.login = login
        self.password = password
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.authenticated = False
        self.server_id = None
        print(f"🔧 Создан клиент Aternos для пользователя: {login}")
        
    def login(self):
        """Логин на Aternos"""
        try:
            print("🔐 Пытаюсь войти в Aternos...")
            # Получаем страницу входа
            resp = self.session.get('https://aternos.org/go/')
            
            # Ищем CSRF токен
            csrf_match = re.search(r'name="csrf_token".*?value="(.*?)"', resp.text)
            csrf_token = csrf_match.group(1) if csrf_match else ''
            
            # Отправляем логин
            data = {
                'user': self.login,
                'password': self.password,
                'csrf_token': csrf_token
            }
            resp = self.session.post('https://aternos.org/login/', data=data)
            
            if 'dashboard' in resp.url or 'panel' in resp.url:
                self.authenticated = True
                print("✅ Успешно вошли в Aternos!")
                return True
            else:
                print("❌ Не удалось войти в Aternos")
                return False
        except Exception as e:
            print(f"❌ Ошибка логина: {e}")
            return False
    
    def get_servers(self):
        """Получить список серверов"""
        if not self.authenticated:
            print("⚠️ Клиент не авторизован, сначала вызовите login()")
            return []
        try:
            resp = self.session.get('https://aternos.org/panel/ajax/servers/')
            data = resp.json()
            servers = data.get('servers', [])
            print(f"📋 Найдено серверов: {len(servers)}")
            return servers
        except Exception as e:
            print(f"❌ Ошибка получения серверов: {e}")
            return []
    
    def start_server(self, server_id):
        """Запустить сервер"""
        if not self.authenticated:
            print("⚠️ Клиент не авторизован, сначала вызовите login()")
            return False
        try:
            print(f"🚀 Отправка запроса на запуск сервера {server_id}...")
            resp = self.session.get(f'https://aternos.org/panel/ajax/start/{server_id}/')
            print(f"📊 Статус ответа: {resp.status_code}")
            return resp.status_code == 200
        except Exception as e:
            print(f"❌ Ошибка запуска: {e}")
            return False

# Создаём глобальный клиент
aternos_client = None

# --- Обработчики команд ---
@dp.message(Command("start"))
async def start_command(message: types.Message):
    print(f"✅ Получена команда /start от {message.from_user.id}")
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="🚀 Запустить сервер")]],
        resize_keyboard=True
    )
    await message.answer(
        "Привет! Нажми кнопку, чтобы запустить Minecraft сервер на Aternos.\n\n"
        "⚠️ Внимание: автоматический запуск через бота может нарушать правила Aternos. Используйте на свой страх и риск.",
        reply_markup=keyboard
    )

@dp.message(lambda message: message.text == "🚀 Запустить сервер")
async def start_server(message: types.Message):
    global aternos_client
    
    if not ATERNOS_LOGIN or not ATERNOS_PASS:
        await message.answer("⚠️ Ошибка: логин или пароль от Aternos не настроены в переменных окружения.")
        return

    await message.answer("🔄 Подключаюсь к Aternos... Это может занять до 30 секунд.")
    print(f"🚀 Пользователь {message.from_user.id} запросил запуск сервера")

    try:
        # Создаём клиент если его нет
        if aternos_client is None:
            print("🔧 Создаю новый клиент Aternos...")
            aternos_client = AternosClient(ATERNOS_LOGIN, ATERNOS_PASS)
            
        # Если клиент не авторизован, пробуем залогиниться
        if not aternos_client.authenticated:
            await message.answer("🔐 Вхожу в Aternos...")
            if not aternos_client.login():
                await message.answer("❌ Не удалось войти в Aternos. Проверьте логин и пароль.")
                return
        
        # Получаем список серверов
        await message.answer("📋 Получаю список серверов...")
        servers = aternos_client.get_servers()
        
        if not servers:
            await message.answer("❌ У вас нет серверов на этом аккаунте Aternos.")
            return
        
        # Берём первый сервер
        server = servers[0]
        server_id = server.get('id')
        server_name = server.get('name', 'Без названия')
        
        print(f"📋 Найден сервер: {server_name} (ID: {server_id})")
        await message.answer(f"🔄 Запускаю сервер '{server_name}'...")
        
        # Запускаем
        if aternos_client.start_server(server_id):
            await message.answer(f"✅ Сервер '{server_name}' успешно запускается!")
            await message.answer("⏳ Обычно сервер готов через 1-2 минуты. Проверьте Aternos.")
        else:
            await message.answer("❌ Не удалось запустить сервер. Возможно, он уже запущен или произошла ошибка.")
            
    except Exception as e:
        print(f"❌ Ошибка при запуске: {e}")
        import traceback
        print(traceback.format_exc())
        await message.answer(f"❌ Ошибка при запуске сервера: {str(e)}")

@dp.message()
async def echo_all(message: types.Message):
    if message.text and not message.text.startswith('/'):
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
        
        future = asyncio.run_coroutine_threadsafe(
            dp.feed_update(bot, update),
            loop
        )
        future.result(timeout=30)
        
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

@app.route("/debug")
def debug():
    """Проверка статуса Aternos"""
    global aternos_client
    if not ATERNOS_LOGIN or not ATERNOS_PASS:
        return "❌ Переменные ATERNOS_LOGIN и ATERNOS_PASS не установлены"
    
    if aternos_client is None:
        return "ℹ️ Клиент Aternos не инициализирован"
    
    return f"ℹ️ Клиент Aternos: {'авторизован' if aternos_client.authenticated else 'не авторизован'}"

# --- Запуск ---
if __name__ == "__main__":
    print(f"🚀 Запуск бота с webhook: {WEBHOOK_URL}")
    print(f"🔑 Aternos логин: {'установлен' if ATERNOS_LOGIN else '❌ НЕ УСТАНОВЛЕН'}")
    print(f"🔑 Aternos пароль: {'установлен' if ATERNOS_PASS else '❌ НЕ УСТАНОВЛЕН'}")
    
    # Запускаем цикл событий в фоновом потоке
    def run_loop():
        loop.run_forever()
    
    thread = threading.Thread(target=run_loop, daemon=True)
    thread.start()
    
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
