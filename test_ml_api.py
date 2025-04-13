#!/usr/bin/env python3
"""
Скрипт для тестирования ML API
"""
import requests
import json
import time
import argparse
import os
from dotenv import load_dotenv
import logging
from typing import Dict, Any, List, Optional
from ml_service.rabbitmq.rabbitmq import publish_message, ML_TASK_QUEUE

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка переменных окружения
load_dotenv()

# URL API
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

def register_user(username: str, password: str, email: str) -> bool:
    """
    Регистрация нового пользователя
    
    Args:
        username: Имя пользователя
        password: Пароль
        email: Email пользователя
        
    Returns:
        bool: True если регистрация успешна, иначе False
    """
    url = f"{API_BASE_URL}/auth/register"
    params = {
        "username": username,
        "password": password,
        "email": email
    }
    
    try:
        response = requests.post(url, params=params)
        if response.status_code == 201 or response.status_code == 200:
            logger.info(f"Пользователь {username} успешно зарегистрирован")
            return True
        else:
            logger.error(f"Ошибка при регистрации: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        logger.error(f"Исключение при регистрации: {e}")
        return False

def login(username, password):
    """
    Авторизация пользователя и получение токена
    
    Args:
        username: Имя пользователя
        password: Пароль
        
    Returns:
        str: Токен доступа
    """
    url = f"{API_BASE_URL}/auth/token"
    data = {
        "username": username,
        "password": password
    }
    
    response = requests.post(url, data=data)
    if response.status_code == 200:
        token_data = response.json()
        return token_data["access_token"]
    else:
        print(f"Ошибка авторизации: {response.status_code} - {response.text}")
        return None

def get_balance(token):
    """
    Получение баланса пользователя
    
    Args:
        token: Токен доступа
        
    Returns:
        float: Баланс пользователя
    """
    url = f"{API_BASE_URL}/users/balance"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        balance_data = response.json()
        return balance_data["balance"]
    else:
        print(f"Ошибка получения баланса: {response.status_code} - {response.text}")
        return None

def make_prediction(token, text):
    """
    Отправка запроса на предсказание
    
    Args:
        token: Токен доступа
        text: Текст для анализа
        
    Returns:
        dict: Информация о задаче предсказания
    """
    url = f"{API_BASE_URL}/predictions/predict"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {
        "data": {
            "text": text
        }
    }
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        prediction_data = response.json()
        return prediction_data
    else:
        print(f"Ошибка отправки задачи: {response.status_code} - {response.text}")
        return None

def check_prediction_status(token, prediction_id):
    """
    Проверка статуса задачи предсказания
    
    Args:
        token: Токен доступа
        prediction_id: ID задачи предсказания
        
    Returns:
        dict: Статус и результат задачи
    """
    url = f"{API_BASE_URL}/predictions/status/{prediction_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        status_data = response.json()
        return status_data
    else:
        print(f"Ошибка проверки статуса: {response.status_code} - {response.text}")
        return None

def get_predictions_history(token):
    """
    Получение истории предсказаний
    
    Args:
        token: Токен доступа
        
    Returns:
        list: История предсказаний
    """
    url = f"{API_BASE_URL}/predictions/history"
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        history_data = response.json()
        return history_data["predictions"]
    else:
        print(f"Ошибка получения истории: {response.status_code} - {response.text}")
        return None

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Тестирование ML API')
    parser.add_argument('--username', required=True, help='Имя пользователя')
    parser.add_argument('--password', required=True, help='Пароль пользователя')
    parser.add_argument('--text', default="Тестовое предсказание", help='Текст для анализа')
    parser.add_argument('--count', type=int, default=5, help='Количество запросов (по умолчанию 5)')
    parser.add_argument('--register', action='store_true', help='Зарегистрировать нового пользователя')
    parser.add_argument('--email', help='Email для регистрации нового пользователя')
    args = parser.parse_args()
    
    # Регистрация пользователя, если указан флаг --register
    if args.register:
        if not args.email:
            print("Для регистрации необходимо указать email (--email)")
            return
        
        if register_user(args.username, args.password, args.email):
            print(f"Пользователь {args.username} успешно зарегистрирован")
        else:
            print("Ошибка при регистрации пользователя")
            return
            
    # Авторизация
    token = login(args.username, args.password)
    if not token:
        print("Не удалось авторизоваться. Проверьте имя пользователя и пароль.")
        return
    
    # Отправка запросов на получение предсказаний
    prediction_ids = []
    for i in range(args.count):
        prediction_id = make_prediction(token, args.text)
        if prediction_id:
            prediction_ids.append(prediction_id)
            print(f"Отправлен запрос №{i+1}, ID предсказания: {prediction_id}")
        else:
            print(f"Ошибка при отправке запроса №{i+1}")
    
    # Проверка результатов предсказаний
    if prediction_ids:
        print("\nРезультаты предсказаний:")
        for i, prediction_id in enumerate(prediction_ids):
            # Ожидаем некоторое время для выполнения предсказания
            time.sleep(1)
            result = check_prediction_status(token, prediction_id)
            if result:
                print(f"Запрос №{i+1}: {json.dumps(result, indent=2, ensure_ascii=False)}")
            else:
                print(f"Не удалось получить результат для запроса №{i+1} (ID: {prediction_id})")
    
    # Получение истории предсказаний
    print("\nИстория предсказаний:")
    history = get_predictions_history(token)
    if history:
        for i, prediction in enumerate(history[:5]):  # Выводим только 5 последних предсказаний
            print(f"Предсказание №{i+1}: {json.dumps(prediction, indent=2, ensure_ascii=False)}")
    else:
        print("Не удалось получить историю предсказаний")

    # Отправка нескольких тестовых сообщений
    for i in range(5):
        message = {
            "user_id": 1, 
            "input_data": {
                "text": f"Тестовое сообщение {i+1}"
            }
        }
        publish_message(message, ML_TASK_QUEUE)
        print(f"Отправлено сообщение {i+1}")

if __name__ == "__main__":
    main() 