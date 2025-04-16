FROM python:3.9-slim

WORKDIR /bot

# Установка инструментов для диагностики
RUN apt-get update && apt-get install -y \
    curl \
    dnsutils \
    iputils-ping \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# Копируем и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY . .

# Устанавливаем переменные окружения для контейнера
ENV PYTHONUNBUFFERED=1
ENV DB_HOST=database
ENV DB_PORT=5432
ENV RABBITMQ_HOST=rabbitmq
ENV RABBITMQ_PORT=5672

# Запуск Telegram бота
CMD ["python", "bot.py"] 