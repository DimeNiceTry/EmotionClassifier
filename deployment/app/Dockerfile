FROM python:3.9-slim

WORKDIR /app

COPY deployment/app/requirements.txt /app/
COPY ml_service /app/ml_service/

RUN pip install --upgrade pip && pip install -r /app/requirements.txt

EXPOSE 8080

CMD ["python", "-m", "ml_service.api.main"] 