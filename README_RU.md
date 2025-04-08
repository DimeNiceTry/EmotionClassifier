# ML Service - Сервис для задач машинного обучения

## Описание проекта

ML Service - это сервис для выполнения задач машинного обучения, где пользователи могут запускать различные ML задачи, потребляя кредиты со своего баланса. 

Система включает:
- REST API на FastAPI для основного взаимодействия
- Telegram-бот для альтернативного доступа
- Базу данных PostgreSQL для хранения данных

## Требования

- Python 3.7+
- PostgreSQL
- Telegram Bot Token (для Telegram-бота)

## Установка

1. Клонировать репозиторий:
```bash
git clone <url-репозитория>
cd ml-service
```

2. Создать и активировать виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Установить зависимости:
```bash
pip install -r requirements.txt
```

4. Настроить переменные окружения в файле `.env`:
```
DATABASE_URL=postgresql://username:password@localhost:5432/ml_service
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
TELEGRAM_BOT_TOKEN=your-telegram-bot-token
API_BASE_URL=http://localhost:8000
```

5. Создать базу данных в PostgreSQL:
```sql
CREATE DATABASE ml_service;
```

## Запуск

### Запуск только REST API:
```bash
uvicorn ml_service.api.main:app --reload
```

API будет доступен по адресу: http://localhost:8000

### Запуск только Telegram-бота:
```bash
python ml_service/bot/run_bot.py
```

### Запуск всех сервисов вместе:
```bash
python start_services.py
```

## Функциональность API

- **Авторизация и регистрация**: `/auth/register`, `/auth/token`
- **Управление балансом**: `/users/balance`, `/users/deposit`
- **Предсказания**: `/predictions/predict`, `/predictions/history`

Полная документация API доступна по адресу: http://localhost:8000/docs

## Функциональность Telegram-бота

- Регистрация и вход
- Просмотр баланса
- Пополнение баланса
- Выполнение предсказаний
- Просмотр истории предсказаний
- Статистика пользователя
