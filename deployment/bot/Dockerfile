FROM python:3.9-slim

WORKDIR /bot

COPY deployment/bot/requirements.txt /bot/
COPY ml_service /bot/ml_service/

RUN pip install --upgrade pip && pip install -r /bot/requirements.txt

CMD ["python", "-m", "ml_service.bot.run_bot"] 