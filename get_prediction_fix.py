@app.get("/predictions/{prediction_id}", response_model=PredictionResponse)
async def get_prediction(
    prediction_id: str,
    current_user: User = Depends(get_current_user)
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            """
            SELECT * FROM predictions 
            WHERE id = %s AND user_id = %s
            """,
            (prediction_id, current_user.id)
        )
        prediction = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")
        
        # Безопасный парсинг JSON с обработкой ошибок
        result = None
        if prediction["result"]:
            try:
                # Проверяем тип данных перед десериализацией
                if isinstance(prediction["result"], dict):
                    result = prediction["result"]
                elif isinstance(prediction["result"], (str, bytes, bytearray)):
                    result = json.loads(prediction["result"])
                else:
                    logger.error(f"Неожиданный тип данных результата для предсказания {prediction_id}: {type(prediction['result'])}")
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка декодирования JSON для предсказания {prediction_id}: {e}")
                # Возвращаем пустой результат вместо ошибки
        
        return PredictionResponse(
            prediction_id=prediction["id"],
            status=prediction["status"],
            result=result,
            timestamp=prediction["created_at"],
            cost=prediction["cost"]
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении предсказания {prediction_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Внутренняя ошибка сервера"
        ) 