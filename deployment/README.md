# ML Service - Docker Deployment

Инструкции по развертыванию ML сервиса с использованием Docker.

## Структура проекта

```
deployment/
├── app/                # Файлы приложения
│   ├── Dockerfile      # Dockerfile для приложения
│   ├── main.py         # Основной скрипт приложения
│   ├── requirements.txt # Зависимости приложения
│   └── .env            # Файл с переменными окружения
├── nginx/              # Конфигурация Nginx
│   └── nginx.conf      # Основной конфигурационный файл Nginx
├── data/               # Папка для данных контейнеров
│   ├── postgres/       # Данные PostgreSQL
│   └── rabbitmq/       # Данные RabbitMQ
└── docker-compose.yaml # Основной файл конфигурации Docker Compose
```

## Сервисы

1. **app** - Основное приложение ML сервиса на FastAPI
2. **web-proxy** - Nginx прокси-сервер
3. **rabbitmq** - Сервис очередей сообщений RabbitMQ
4. **database** - База данных PostgreSQL

## Запуск проекта

Для запуска проекта выполните:

```bash
cd deployment
docker-compose up -d
```

## Доступ к сервисам

- **API**: http://localhost:80
- **RabbitMQ Management**: http://localhost:15672 (guest/guest)
- **PostgreSQL**: localhost:5432 (postgres/postgres)

## Остановка проекта

```bash
docker-compose down
```

## Очистка всех данных

```bash
docker-compose down -v
``` 