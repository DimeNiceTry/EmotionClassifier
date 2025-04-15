from ml_service.database.database import get_db_session
from ml_service.database.models import Prediction, User
import json

def main():
    # Получение сессии базы данных
    session = next(get_db_session())
    
    try:
        # Получение всех предсказаний
        predictions = session.query(Prediction).order_by(Prediction.created_at.desc()).all()
        
        print(f"Всего предсказаний: {len(predictions)}")
        print("\nПоследние 5 предсказаний:")
        
        # Вывод последних 5 предсказаний
        for p in predictions[:5]:
            # Получение пользователя
            user = session.query(User).filter(User.id == p.user_id).first()
            username = user.username if user else "Неизвестный пользователь"
            
            print(f"ID: {p.id}, Пользователь: {username} (ID: {p.user_id})")
            print(f"Сырые входные данные: {p.input_data}")
            print(f"Сырые данные результата: {p.result}")
            
            # Парсинг JSON результата
            try:
                result_data = json.loads(p.result)
                result_text = result_data.get('result', {}).get('prediction', 'Нет данных')
                confidence = result_data.get('result', {}).get('confidence', 'Нет данных')
            except Exception as e:
                result_text = f"Ошибка парсинга JSON: {e}"
                confidence = "Ошибка парсинга JSON"
            
            # Парсинг входных данных
            try:
                input_data = json.loads(p.input_data)
                input_text = input_data.get('text', 'Нет данных')
            except Exception as e:
                input_text = f"Ошибка парсинга JSON: {e}"
            
            print(f"Входной текст: {input_text}")
            print(f"Результат: {result_text}, Достоверность: {confidence}")
            print(f"Стоимость: {p.cost}, Время: {p.created_at}")
            print("-" * 50)
    
    except Exception as e:
        print(f"Ошибка при получении предсказаний: {e}")
    
    finally:
        session.close()

if __name__ == "__main__":
    main() 