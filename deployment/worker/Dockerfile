FROM python:3.9-slim

WORKDIR /worker

COPY deployment/worker/requirements.txt /worker/
COPY ml_service /worker/ml_service/

RUN pip install --upgrade pip && pip install -r /worker/requirements.txt

CMD ["python", "-m", "ml_service.rabbitmq.worker"] 