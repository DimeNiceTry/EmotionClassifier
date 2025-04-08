import requests
import json

# Базовый URL API
base_url = "http://localhost:8000"

# Регистрация пользователя
def register_user():
    url = f"{base_url}/auth/register"
    params = {
        "username": "test_user", 
        "password": "password123", 
        "email": "test@example.com",
        "full_name": "Test User"  # Опционально
    }
    response = requests.post(url, params=params)
    print(f"Регистрация: {response.status_code}")
    print(response.json() if response.status_code < 400 else response.text)

# Получение токена
def get_token():
    url = f"{base_url}/auth/token"
    data = {
        "username": "test_user",
        "password": "password123"
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(url, data=data, headers=headers)
    print(f"Получение токена: {response.status_code}")
    print(response.json() if response.status_code < 400 else response.text)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    return None

# Пополнение баланса
def deposit_balance(token, amount=100):
    url = f"{base_url}/users/deposit"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"amount": amount}
    response = requests.post(url, params=params, headers=headers)
    print(f"Пополнение баланса: {response.status_code}")
    print(response.json() if response.status_code < 400 else response.text)

# Выполнение предсказания
def make_prediction(token):
    url = f"{base_url}/predictions/predict"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    data = {"data": {"text": "Будет ли завтра хорошая погода?"}}
    response = requests.post(url, json=data, headers=headers)
    print(f"Предсказание: {response.status_code}")
    print(response.json() if response.status_code < 400 else response.text)

# Получение баланса
def get_balance(token):
    url = f"{base_url}/users/balance"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print(f"Баланс: {response.status_code}")
    print(response.json() if response.status_code < 400 else response.text)

# Получение истории предсказаний
def get_history(token):
    url = f"{base_url}/predictions/history"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    print(f"История предсказаний: {response.status_code}")
    print(response.json() if response.status_code < 400 else response.text)

# Запуск тестов
if __name__ == "__main__":
    # Попытка регистрации (может вернуть ошибку, если пользователь уже существует)
    register_user()
    
    # Получение токена
    token = get_token()
    if not token:
        print("Не удалось получить токен, завершение работы.")
        exit(1)
    
    # Получение текущего баланса
    get_balance(token)
    
    # Пополнение баланса
    deposit_balance(token, 100)
    
    # Проверка баланса после пополнения
    get_balance(token)
    
    # Отправка запроса на предсказание
    make_prediction(token)
    
    # Проверка баланса после предсказания
    get_balance(token)
    
    # Получение истории предсказаний
    get_history(token)