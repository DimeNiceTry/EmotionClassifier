#!/usr/bin/env python3
"""
Скрипт для отправки настраиваемых сообщений в очередь предсказаний
"""
from ml_service.rabbitmq.rabbitmq import publish_message, ML_TASK_QUEUE
import time
from datetime import datetime

# Настройки пользователя (можно изменить на нужного пользователя)
USER_ID = 18  # ID пользователя (new_test_user)

# Получаем текущую временную метку для идентификации этого набора сообщений
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Различные тестовые сообщения для демонстрации разных предсказаний
test_messages = [
    f"[{timestamp}] Это очень хороший результат, я доволен успехом проекта!",
    f"[{timestamp}] К сожалению, это плохой результат и неудача проекта.",
    f"[{timestamp}] Не могу точно сказать, результат неопределенный.",
    f"[{timestamp}] Мы достигли отличных показателей, всё идёт положительно!",
    f"[{timestamp}] Проект провалился, все показатели отрицательные."
]

print(f"Отправка сообщений для пользователя с ID: {USER_ID}")
print(f"Временная метка для идентификации: {timestamp}")

for i, text in enumerate(test_messages):
    message = {
        "user_id": USER_ID, 
        "input_data": {
            "text": text
        }
    }
    publish_message(message, ML_TASK_QUEUE)
    print(f"Отправлено сообщение {i+1}: {text[:50]}...")
    time.sleep(0.5)  # Небольшая пауза между сообщениями

print("Все сообщения успешно отправлены") 