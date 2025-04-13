from ml_service.rabbitmq.rabbitmq import publish_message, ML_TASK_QUEUE

for i in range(10):
    message = {
        "user_id": 1, 
        "input_data": {
            "text": f"Тестовое сообщение {i+1}"
        }
    }
    publish_message(message, ML_TASK_QUEUE)
    print(f"Отправлено сообщение {i+1}")