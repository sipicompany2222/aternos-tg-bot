import requests
import json
import time
import re

class AternosAPI:
    def init(self, login, password):
        self.session = requests.Session()
        self.login = login
        self.password = password
        self.base_url = "https://aternos.org"
        self.authenticated = False
        self.server_id = None
        
    def login(self):
        """Логин на Aternos"""
        try:
            # Получаем CSRF токен
            resp = self.session.get(f"{self.base_url}/go/")
            csrf_token = re.search(r'name="csrf_token".*?value="(.*?)"', resp.text)
            if csrf_token:
                csrf_token = csrf_token.group(1)
            else:
                csrf_token = ""
            
            # Отправляем логин
            data = {
                "user": self.login,
                "password": self.password,
                "csrf_token": csrf_token
            }
            resp = self.session.post(f"{self.base_url}/login/", data=data)
            
            if "dashboard" in resp.url:
                self.authenticated = True
                return True
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def get_servers(self):
        """Получить список серверов"""
        if not self.authenticated:
            return []
        
        try:
            resp = self.session.get(f"{self.base_url}/panel/ajax/servers/")
            data = resp.json()
            return data.get("servers", [])
        except:
            return []
    
    def start_server(self, server_id):
        """Запустить сервер по ID"""
        if not self.authenticated:
            return False
        
        try:
            resp = self.session.get(f"{self.base_url}/panel/ajax/start/{server_id}/")
            return resp.status_code == 200
        except:
            return False
    
    def get_server_status(self, server_id):
        """Получить статус сервера"""
        if not self.authenticated:
            return "offline"
        
        try:
            resp = self.session.get(f"{self.base_url}/panel/ajax/status/{server_id}/")
            data = resp.json()
            return data.get("status", "offline")
        except:
            return "offline"
