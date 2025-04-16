// API URL
const API_URL = '';

/**
 * Выполняет HTTP запрос к API
 * @param {string} endpoint - Эндпоинт API
 * @param {string} method - HTTP метод
 * @param {Object} data - Данные для отправки
 * @param {boolean} auth - Требуется ли аутентификация
 * @returns {Promise<any>} - Результат запроса
 */
async function fetchAPI(endpoint, method = 'GET', data = null, auth = true) {
    const url = `${API_URL}${endpoint}`;
    const headers = {
        'Content-Type': 'application/json',
    };

    // Добавляем токен авторизации, если требуется
    if (auth) {
        const token = localStorage.getItem('token');
        if (!token) {
            throw new Error('Требуется авторизация');
        }
        headers['Authorization'] = `Bearer ${token}`;
    }

    const options = {
        method,
        headers,
        credentials: 'include',
    };

    // Добавляем тело запроса для методов, которые его поддерживают
    if (data && ['POST', 'PUT', 'PATCH'].includes(method)) {
        options.body = JSON.stringify(data);
    }

    try {
        console.log(`[API] ${method} ${url}`, options);
        const response = await fetch(url, options);
        
        // Проверяем, есть ли тело ответа
        const contentType = response.headers.get('content-type');
        
        // Обработка ошибок HTTP
        if (!response.ok) {
            let errorMessage = 'Произошла ошибка при выполнении запроса';
            
            try {
                if (contentType && contentType.includes('application/json')) {
                    const errorData = await response.json();
                    errorMessage = errorData.detail || errorMessage;
                } else {
                    errorMessage = await response.text() || errorMessage;
                    // Если текст ошибки слишком длинный, оставляем только начало
                    if (errorMessage.length > 100) {
                        errorMessage = errorMessage.substring(0, 100) + '...';
                    }
                }
            } catch (parseError) {
                console.error('Ошибка при обработке ответа сервера:', parseError);
                errorMessage = `Ошибка ${response.status}: ${response.statusText}`;
            }
            
            throw new Error(errorMessage);
        }
        
        if (!contentType) {
            console.log(`[API] Ответ без Content-Type`, response);
            return null;
        }
        
        let responseData;
        if (contentType.includes('application/json')) {
            try {
                responseData = await response.json();
                console.log(`[API] JSON ответ:`, responseData);
                return responseData;
            } catch (jsonError) {
                console.error('Ошибка при разборе JSON:', jsonError);
                throw new Error('Получен некорректный JSON от сервера');
            }
        }
        
        const textResponse = await response.text();
        console.log(`[API] Текстовый ответ:`, textResponse);
        return textResponse;
    } catch (error) {
        if (error.name === 'TypeError' && error.message.includes('Failed to fetch')) {
            console.error('Ошибка сети при запросе к API:', error);
            throw new Error('Не удалось подключиться к серверу. Проверьте подключение к интернету.');
        }
        
        console.error('Ошибка API:', error);
        throw error;
    }
}

/**
 * API для работы с аутентификацией
 */
const AuthAPI = {
    /**
     * Получение токена доступа
     * @param {string} username - Имя пользователя
     * @param {string} password - Пароль
     * @returns {Promise<{access_token: string, token_type: string}>} - Токен доступа
     */
    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        try {
            const response = await fetch(`${API_URL}/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: formData,
            });

            const contentType = response.headers.get('content-type');
            
            if (!response.ok) {
                let errorMessage = 'Ошибка при авторизации';
                
                try {
                    if (contentType && contentType.includes('application/json')) {
                        const errorData = await response.json();
                        errorMessage = errorData.detail || errorMessage;
                    } else {
                        errorMessage = await response.text() || errorMessage;
                        // Если текст ошибки слишком длинный, оставляем только начало
                        if (errorMessage.length > 100) {
                            errorMessage = errorMessage.substring(0, 100) + '...';
                        }
                    }
                } catch (parseError) {
                    console.error('Ошибка при обработке ответа сервера:', parseError);
                }
                
                throw new Error(errorMessage);
            }

            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            throw new Error('Неверный формат ответа от сервера');
        } catch (error) {
            console.error('Ошибка при авторизации:', error);
            throw error;
        }
    },

    /**
     * Регистрация нового пользователя
     * @param {string} username - Имя пользователя
     * @param {string} password - Пароль
     * @param {string} email - Email (опционально)
     * @returns {Promise<Object>} - Информация о пользователе
     */
    async register(username, password, email = null) {
        const data = { username, password };
        if (email) {
            data.email = email;
        }

        return await fetchAPI('/users', 'POST', data, false);
    },

    /**
     * Получение информации о текущем пользователе
     * @returns {Promise<Object>} - Информация о пользователе
     */
    async getCurrentUser() {
        return await fetchAPI('/users/me', 'GET');
    }
};

/**
 * API для работы с предсказаниями
 */
const PredictionAPI = {
    /**
     * Создание нового предсказания
     * @param {string} text - Текст для предсказания
     * @returns {Promise<Object>} - Информация о предсказании
     */
    async makePrediction(text) {
        const data = {
            data: { text: text.trim() }
        };
        console.log('Отправляем данные для предсказания:', data);
        try {
            const result = await fetchAPI('/predictions/predict', 'POST', data);
            console.log('Получен ответ от сервера:', result);
            return result;
        } catch (error) {
            console.error('Ошибка API предсказания:', error);
            throw error;
        }
    },

    /**
     * Получение информации о предсказании
     * @param {string} id - Идентификатор предсказания
     * @returns {Promise<Object>} - Информация о предсказании
     */
    async getPrediction(id) {
        if (!id) {
            throw new Error('Не указан идентификатор предсказания');
        }
        
        let retries = 0;
        const maxRetries = 3;
        const retryDelay = 1000; // 1 секунда
        
        while (retries < maxRetries) {
            try {
                console.log(`Запрос статуса предсказания ${id} (попытка ${retries + 1}/${maxRetries})`);
                const result = await fetchAPI(`/predictions/${id}`, 'GET');
                console.log(`Получен статус предсказания ${id}:`, result);
                return result;
            } catch (error) {
                retries++;
                console.error(`Ошибка при получении статуса предсказания ${id} (попытка ${retries}/${maxRetries}):`, error);
                
                // Если это последняя попытка или ошибка не связана с сетью/сервером, прокидываем дальше
                if (retries >= maxRetries || (error.message && !error.message.includes('сервер'))) {
                    throw error;
                }
                
                // Ждем перед повторной попыткой
                console.log(`Ожидание ${retryDelay}мс перед следующей попыткой...`);
                await new Promise(resolve => setTimeout(resolve, retryDelay));
            }
        }
    },

    /**
     * Получение истории предсказаний
     * @returns {Promise<Object>} - История предсказаний
     */
    async getPredictionHistory() {
        let retries = 0;
        const maxRetries = 3;
        const retryDelay = 1000; // 1 секунда
        
        while (retries < maxRetries) {
            try {
                console.log(`Запрос истории предсказаний (попытка ${retries + 1}/${maxRetries})`);
                const result = await fetchAPI('/predictions', 'GET');
                console.log(`Получена история предсказаний:`, result);
                return result;
            } catch (error) {
                retries++;
                console.error(`Ошибка при получении истории предсказаний (попытка ${retries}/${maxRetries}):`, error);
                
                // Если это последняя попытка или ошибка не связана с сетью/сервером, прокидываем дальше
                if (retries >= maxRetries || (error.message && !error.message.includes('сервер'))) {
                    throw error;
                }
                
                // Ждем перед повторной попыткой
                console.log(`Ожидание ${retryDelay}мс перед следующей попыткой...`);
                await new Promise(resolve => setTimeout(resolve, retryDelay));
            }
        }
    }
};

/**
 * API для работы с балансом
 */
const BalanceAPI = {
    /**
     * Получение текущего баланса
     * @returns {Promise<Object>} - Текущий баланс
     */
    async getBalance() {
        return await fetchAPI('/balance', 'GET');
    },
    
    /**
     * Пополнение баланса
     * @param {number} amount - Сумма пополнения
     * @returns {Promise<Object>} - Результат операции
     */
    async topUpBalance(amount) {
        const data = { amount: parseFloat(amount) };
        return await fetchAPI('/balance/topup', 'POST', data);
    }
}; 