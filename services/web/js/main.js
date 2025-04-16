/**
 * Основной класс для управления приложением
 */
class App {
    constructor() {
        // Инициализация аутентификации
        this.auth = new Auth();
        
        // DOM элементы для навигации
        this.navLinks = document.querySelectorAll('#main-nav a');
        this.sections = document.querySelectorAll('.section');
        
        // Формы и элементы для предсказаний
        this.predictionForm = document.getElementById('prediction-form');
        this.predictionText = document.getElementById('prediction-text');
        this.predictionResult = document.getElementById('prediction-result');
        this.resultContent = document.getElementById('result-content');
        this.historyList = document.getElementById('history-list');
        this.currentBalance = document.getElementById('current-balance');
        
        // Элементы для пополнения баланса
        this.topupForm = document.getElementById('topup-form');
        this.topupAmount = document.getElementById('topup-amount');
        this.topupResult = document.getElementById('topup-result');
        this.topupError = document.getElementById('topup-error');
        this.previousBalance = document.getElementById('previous-balance');
        this.newBalance = document.getElementById('new-balance');
        
        // Привязываем обработчики событий
        this.bindEvents();
        
        // Проверяем статус аутентификации
        this.auth.checkAuthStatus().then(() => {
            // Если пользователь авторизован, загружаем данные
            if (this.auth.isLoggedIn()) {
                this.loadBalance();
                this.loadPredictionHistory();
            }
        });
    }
    
    /**
     * Привязывает обработчики событий
     */
    bindEvents() {
        // Навигация
        this.navLinks.forEach(link => {
            link.addEventListener('click', this.handleNavigation.bind(this));
        });
        
        // Обработка формы предсказания
        this.predictionForm.addEventListener('submit', this.handlePrediction.bind(this));
        
        // Обработка формы пополнения баланса
        this.topupForm.addEventListener('submit', this.handleTopUp.bind(this));
    }
    
    /**
     * Обработчик навигации по разделам
     * @param {Event} event - Событие клика
     */
    handleNavigation(event) {
        event.preventDefault();
        
        const targetId = event.target.id;
        const sectionId = targetId.replace('nav-', '') + '-section';
        
        // Если пользователь не авторизован и пытается перейти в защищенный раздел
        if (!this.auth.isLoggedIn() && targetId !== 'nav-home') {
            this.auth.showLoginModal();
            return;
        }
        
        // Активируем выбранный пункт меню
        this.navLinks.forEach(link => {
            link.classList.remove('active');
        });
        event.target.classList.add('active');
        
        // Показываем выбранный раздел
        this.sections.forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(sectionId).classList.add('active');
        
        // Обновляем данные при переходе в раздел
        if (this.auth.isLoggedIn()) {
            if (targetId === 'nav-history') {
                this.loadPredictionHistory();
            } else if (targetId === 'nav-balance') {
                this.loadBalance();
            }
        }
    }
    
    /**
     * Обработчик отправки формы предсказания
     * @param {Event} event - Событие отправки формы
     */
    async handlePrediction(event) {
        event.preventDefault();
        
        if (!this.auth.isLoggedIn()) {
            this.auth.showLoginModal();
            return;
        }
        
        const text = this.predictionText.value.trim();
        
        if (!text) {
            alert('Пожалуйста, введите текст для предсказания');
            return;
        }
        
        // Показываем индикатор загрузки
        this.resultContent.innerHTML = '<div class="loading">Выполняем предсказание...</div>';
        this.predictionResult.classList.remove('hidden');
        
        try {
            // Отправляем запрос на предсказание
            console.log('Отправка текста для предсказания:', text);
            const prediction = await PredictionAPI.makePrediction(text);
            
            console.log('Результат запроса предсказания:', prediction);
            
            if (!prediction || !prediction.prediction_id) {
                throw new Error('Не получен идентификатор предсказания от сервера');
            }
            
            // Проверяем статус предсказания
            if (prediction.status === 'pending') {
                // Если предсказание в очереди, начинаем опрос статуса
                // Сначала показываем начальный статус
                this.displayPredictionResult(prediction);
                
                // Начинаем проверять статус через 2 секунды
                setTimeout(() => {
                    this.checkPredictionStatus(prediction.prediction_id);
                }, 2000);
            } else {
                // Если предсказание выполнено, показываем результат
                this.displayPredictionResult(prediction);
                // Обновляем баланс
                this.loadBalance();
            }
        } catch (error) {
            console.error('Ошибка при выполнении предсказания:', error);
            
            if (error.message && (error.message.includes('баланс') || error.message.includes('средств'))) {
                // Ошибка связана с балансом
                this.resultContent.innerHTML = `
                    <div class="error">
                        <p>Недостаточно средств на балансе для выполнения предсказания.</p>
                        <p>Пожалуйста, пополните баланс в разделе "Баланс".</p>
                        <button class="btn btn-primary" id="go-to-balance">Перейти к пополнению</button>
                    </div>
                `;
                
                // Добавляем обработчик для кнопки
                setTimeout(() => {
                    const balanceBtn = document.getElementById('go-to-balance');
                    if (balanceBtn) {
                        balanceBtn.addEventListener('click', () => {
                            document.getElementById('nav-balance').click();
                        });
                    }
                }, 100);
            } else if (error.message && error.message.includes('Internal Server Error')) {
                this.resultContent.innerHTML = `
                    <div class="error">
                        <p>Сервер временно недоступен. Пожалуйста, повторите попытку позже.</p>
                        <p>Если проблема сохраняется, обратитесь в службу поддержки.</p>
                    </div>
                `;
            } else {
                this.resultContent.innerHTML = `
                    <div class="error">
                        <p>Ошибка при выполнении предсказания: ${error.message}</p>
                    </div>
                `;
            }
        }
    }
    
    /**
     * Периодически проверяет статус предсказания
     * @param {string} predictionId - Идентификатор предсказания
     */
    async checkPredictionStatus(predictionId) {
        if (!predictionId) {
            console.error('Некорректный ID предсказания:', predictionId);
            this.resultContent.innerHTML = `
                <div class="error">
                    <p>Ошибка: некорректный идентификатор предсказания</p>
                </div>
            `;
            return;
        }

        try {
            console.log('Проверка статуса предсказания:', predictionId);
            
            // Получаем статус предсказания
            const prediction = await PredictionAPI.getPrediction(predictionId);
            
            console.log('Результат проверки статуса:', prediction);
            
            // Если предсказание завершено, показываем результат
            if (prediction.status !== 'pending') {
                this.displayPredictionResult(prediction);
                // Обновляем баланс
                this.loadBalance();
                return;
            }
            
            // Если предсказание все еще в очереди, продолжаем проверку
            this.resultContent.innerHTML = `
                <div class="prediction-content">
                    <p>Предсказание в процессе обработки... Ожидайте результата.</p>
                    <div class="loading-spinner"></div>
                </div>
            `;
            
            // Увеличиваем интервал проверки с каждой попыткой
            const retryCount = this.predictionRetryCount || 0;
            this.predictionRetryCount = retryCount + 1;
            
            const baseDelay = 2000; // 2 секунды
            const maxDelay = 10000; // 10 секунд
            let delay = Math.min(baseDelay * Math.pow(1.5, retryCount), maxDelay);
            
            console.log(`Следующая проверка через ${delay}мс (попытка ${this.predictionRetryCount})`);
            
            setTimeout(() => {
                this.checkPredictionStatus(predictionId);
            }, delay);
        } catch (error) {
            console.error('Ошибка при проверке статуса предсказания:', error);
            
            // Если ошибка связана с отсутствием предсказания
            if (error.message && error.message.includes('not found')) {
                this.resultContent.innerHTML = `
                    <div class="error">
                        <p>Предсказание не найдено. Возможно, оно было удалено или произошла ошибка.</p>
                    </div>
                `;
            } else if (error.message && error.message.includes('Internal Server Error')) {
                // Если внутренняя ошибка сервера, попробуем еще раз через некоторое время
                this.resultContent.innerHTML = `
                    <div class="prediction-content">
                        <p>Предсказание в процессе обработки. Возникли временные трудности, пытаемся получить результат...</p>
                        <div class="loading-spinner"></div>
                    </div>
                `;
                
                // Максимальное количество повторных попыток при ошибке
                const maxErrorRetries = 3;
                const errorRetryCount = this.predictionErrorRetryCount || 0;
                this.predictionErrorRetryCount = errorRetryCount + 1;
                
                if (this.predictionErrorRetryCount <= maxErrorRetries) {
                    const errorRetryDelay = 5000; // 5 секунд
                    console.log(`Повторная попытка после ошибки через ${errorRetryDelay}мс (попытка ${this.predictionErrorRetryCount}/${maxErrorRetries})`);
                    
                    setTimeout(() => {
                        this.checkPredictionStatus(predictionId);
                    }, errorRetryDelay);
                } else {
                    this.resultContent.innerHTML = `
                        <div class="error">
                            <p>Не удалось получить результат предсказания из-за технических проблем.</p>
                            <p>Пожалуйста, проверьте статус позже в разделе "История предсказаний".</p>
                            <button class="btn btn-primary" id="go-to-history">Перейти к истории</button>
                        </div>
                    `;
                    
                    // Добавляем обработчик для кнопки
                    setTimeout(() => {
                        const historyBtn = document.getElementById('go-to-history');
                        if (historyBtn) {
                            historyBtn.addEventListener('click', () => {
                                document.getElementById('nav-history').click();
                            });
                        }
                    }, 100);
                }
            } else {
                // Другие ошибки
                this.resultContent.innerHTML = `
                    <div class="error">
                        <p>Ошибка при проверке статуса предсказания: ${error.message}</p>
                        <p>Попробуйте обновить страницу или повторить запрос позже.</p>
                    </div>
                `;
            }
        }
    }
    
    /**
     * Отображает результат предсказания
     * @param {Object} prediction - Информация о предсказании
     */
    displayPredictionResult(prediction) {
        if (!prediction) {
            this.resultContent.innerHTML = `
                <div class="error">
                    <p>Ошибка: Не удалось получить информацию о предсказании</p>
                </div>
            `;
            return;
        }

        let statusClass = 'status-pending';
        let statusText = 'В обработке';
        
        if (prediction.status === 'completed') {
            statusClass = 'status-completed';
            statusText = 'Выполнено';
        } else if (prediction.status === 'failed') {
            statusClass = 'status-failed';
            statusText = 'Ошибка';
        }
        
        // Форматируем дату
        let timestamp = 'Неизвестно';
        try {
            if (prediction.timestamp) {
                timestamp = new Date(prediction.timestamp).toLocaleString('ru-RU');
            }
        } catch (e) {
            console.error('Ошибка форматирования даты:', e, prediction);
        }
        
        // Отображаем результат
        let resultHtml = `
            <div class="prediction-meta">
                <span>ID: ${prediction.prediction_id || 'N/A'}</span>
                <span class="${statusClass}">${statusText}</span>
                <span>Стоимость: ${prediction.cost || '1.0'} кредитов</span>
                <span>Дата: ${timestamp}</span>
            </div>
        `;
        
        try {
            if (prediction.status === 'completed' && prediction.result) {
                // Форматируем результат в зависимости от типа данных
                let resultText = '';
                
                if (typeof prediction.result === 'object') {
                    resultText = `<pre>${JSON.stringify(prediction.result, null, 2)}</pre>`;
                } else {
                    resultText = prediction.result;
                }
                
                resultHtml += `
                    <div class="prediction-content">
                        <h4>Результат:</h4>
                        ${resultText}
                    </div>
                `;
            } else if (prediction.status === 'failed') {
                resultHtml += `
                    <div class="prediction-content error">
                        <p>Не удалось выполнить предсказание. Пожалуйста, попробуйте еще раз.</p>
                    </div>
                `;
            } else {
                resultHtml += `
                    <div class="prediction-content">
                        <p>Предсказание в процессе обработки. Пожалуйста, подождите.</p>
                        <div class="loading">Обработка...</div>
                    </div>
                `;
            }
        } catch (e) {
            console.error('Ошибка при форматировании результата предсказания:', e, prediction);
            resultHtml += `
                <div class="prediction-content error">
                    <p>Произошла ошибка при отображении результата. Детали в консоли.</p>
                </div>
            `;
        }
        
        this.resultContent.innerHTML = resultHtml;
    }
    
    /**
     * Загружает историю предсказаний
     */
    async loadPredictionHistory() {
        if (!this.auth.isLoggedIn()) {
            this.predictionHistoryContent.innerHTML = `
                <div class="not-authenticated">
                    <p>Для просмотра истории предсказаний необходимо авторизоваться</p>
                    <button class="btn btn-primary" id="login-for-history">Войти</button>
                </div>
            `;
            
            setTimeout(() => {
                const loginBtn = document.getElementById('login-for-history');
                if (loginBtn) {
                    loginBtn.addEventListener('click', () => {
                        this.auth.showLoginModal();
                    });
                }
            }, 100);
            
            return;
        }
        
        this.predictionHistoryContent.innerHTML = `
            <div class="loading">Загрузка истории предсказаний...</div>
        `;
        
        try {
            // Получаем историю предсказаний
            const history = await PredictionAPI.getPredictionHistory();
            
            if (!history || !history.predictions || history.predictions.length === 0) {
                this.predictionHistoryContent.innerHTML = `
                    <div class="empty-history">
                        <p>У вас пока нет предсказаний</p>
                        <button class="btn btn-primary" id="make-first-prediction">Сделать первое предсказание</button>
                    </div>
                `;
                
                setTimeout(() => {
                    const predictionBtn = document.getElementById('make-first-prediction');
                    if (predictionBtn) {
                        predictionBtn.addEventListener('click', () => {
                            document.getElementById('nav-predict').click();
                        });
                    }
                }, 100);
                
                return;
            }
            
            // Сортируем по дате (новые сверху)
            const sortedPredictions = [...history.predictions].sort((a, b) => {
                return new Date(b.timestamp) - new Date(a.timestamp);
            });
            
            // Формируем HTML для истории
            let historyHtml = `<div class="prediction-history-list">`;
            
            for (const prediction of sortedPredictions) {
                let statusClass = 'status-pending';
                let statusText = 'В обработке';
                
                if (prediction.status === 'completed') {
                    statusClass = 'status-completed';
                    statusText = 'Выполнено';
                } else if (prediction.status === 'failed') {
                    statusClass = 'status-failed';
                    statusText = 'Ошибка';
                }
                
                // Форматируем дату
                let timestamp = 'Неизвестно';
                try {
                    if (prediction.timestamp) {
                        timestamp = new Date(prediction.timestamp).toLocaleString('ru-RU');
                    }
                } catch (e) {
                    console.error('Ошибка форматирования даты:', e, prediction);
                }
                
                // Формируем результат
                let resultHtml = '';
                if (prediction.status === 'completed' && prediction.result) {
                    try {
                        if (prediction.result.prediction && prediction.result.confidence) {
                            const confidence = (prediction.result.confidence * 100).toFixed(1);
                            resultHtml = `
                                <div class="prediction-result">
                                    <p>Результат: <strong>${prediction.result.prediction}</strong></p>
                                    <p>Уверенность: <strong>${confidence}%</strong></p>
                                </div>
                            `;
                        } else if (prediction.result.error) {
                            resultHtml = `
                                <div class="prediction-result error">
                                    <p>Ошибка: ${prediction.result.error}</p>
                                </div>
                            `;
                        } else {
                            resultHtml = `
                                <div class="prediction-result">
                                    <pre>${JSON.stringify(prediction.result, null, 2)}</pre>
                                </div>
                            `;
                        }
                    } catch (e) {
                        console.error('Ошибка форматирования результата:', e, prediction);
                        resultHtml = `
                            <div class="prediction-result error">
                                <p>Ошибка отображения результата</p>
                            </div>
                        `;
                    }
                } else if (prediction.status === 'pending') {
                    resultHtml = `
                        <div class="prediction-result pending">
                            <p>Ожидание результата...</p>
                            <button class="btn btn-sm btn-primary check-status" data-id="${prediction.prediction_id}">Проверить статус</button>
                        </div>
                    `;
                } else if (prediction.status === 'failed') {
                    resultHtml = `
                        <div class="prediction-result error">
                            <p>Не удалось выполнить предсказание</p>
                        </div>
                    `;
                }
                
                // Формируем итоговую карточку
                historyHtml += `
                    <div class="prediction-item">
                        <div class="prediction-header">
                            <span class="prediction-id">ID: ${prediction.prediction_id}</span>
                            <span class="prediction-date">${timestamp}</span>
                            <span class="prediction-status ${statusClass}">${statusText}</span>
                            <span class="prediction-cost">Стоимость: ${prediction.cost} кредитов</span>
                        </div>
                        ${resultHtml}
                    </div>
                `;
            }
            
            historyHtml += `</div>`;
            
            this.predictionHistoryContent.innerHTML = historyHtml;
            
            // Добавляем обработчики для кнопок проверки статуса
            setTimeout(() => {
                const checkButtons = document.querySelectorAll('.check-status');
                checkButtons.forEach(button => {
                    button.addEventListener('click', async (event) => {
                        const predictionId = event.target.dataset.id;
                        if (predictionId) {
                            // Показываем индикатор загрузки вместо кнопки
                            event.target.parentNode.innerHTML = `
                                <p>Проверка статуса...</p>
                                <div class="loading-spinner small"></div>
                            `;
                            
                            try {
                                const prediction = await PredictionAPI.getPrediction(predictionId);
                                
                                // Перезагружаем всю историю для обновления данных
                                this.loadPredictionHistory();
                            } catch (error) {
                                console.error('Ошибка при проверке статуса:', error);
                                event.target.parentNode.innerHTML = `
                                    <p class="error">Ошибка при проверке статуса</p>
                                    <button class="btn btn-sm btn-primary check-status" data-id="${predictionId}">Повторить</button>
                                `;
                                
                                // Заново добавляем обработчик
                                setTimeout(() => {
                                    const newButton = event.target.parentNode.querySelector('.check-status');
                                    if (newButton) {
                                        newButton.addEventListener('click', this.handleCheckStatusClick.bind(this));
                                    }
                                }, 100);
                            }
                        }
                    });
                });
            }, 100);
        } catch (error) {
            console.error('Ошибка при загрузке истории предсказаний:', error);
            
            // Проверяем тип ошибки
            if (error.message && error.message.includes('авторизац')) {
                // Ошибка авторизации
                this.predictionHistoryContent.innerHTML = `
                    <div class="error">
                        <p>Для просмотра истории предсказаний необходимо авторизоваться</p>
                        <button class="btn btn-primary" id="login-for-history-error">Войти</button>
                    </div>
                `;
                
                setTimeout(() => {
                    const loginBtn = document.getElementById('login-for-history-error');
                    if (loginBtn) {
                        loginBtn.addEventListener('click', () => {
                            this.auth.showLoginModal();
                        });
                    }
                }, 100);
            } else if (error.message && error.message.includes('Internal Server Error')) {
                // Внутренняя ошибка сервера
                this.predictionHistoryContent.innerHTML = `
                    <div class="error">
                        <p>Ошибка при загрузке истории предсказаний: Внутренняя ошибка сервера</p>
                        <p>Попробуйте обновить страницу через некоторое время.</p>
                        <button class="btn btn-primary" id="retry-history">Повторить попытку</button>
                    </div>
                `;
                
                setTimeout(() => {
                    const retryBtn = document.getElementById('retry-history');
                    if (retryBtn) {
                        retryBtn.addEventListener('click', () => {
                            this.loadPredictionHistory();
                        });
                    }
                }, 100);
            } else {
                // Другие ошибки
                this.predictionHistoryContent.innerHTML = `
                    <div class="error">
                        <p>Ошибка при загрузке истории предсказаний: ${error.message}</p>
                        <button class="btn btn-primary" id="retry-history">Повторить попытку</button>
                    </div>
                `;
                
                setTimeout(() => {
                    const retryBtn = document.getElementById('retry-history');
                    if (retryBtn) {
                        retryBtn.addEventListener('click', () => {
                            this.loadPredictionHistory();
                        });
                    }
                }, 100);
            }
        }
    }
    
    // Вспомогательный метод для обработки кликов по кнопке проверки статуса
    async handleCheckStatusClick(event) {
        const predictionId = event.target.dataset.id;
        if (predictionId) {
            // Показываем индикатор загрузки вместо кнопки
            event.target.parentNode.innerHTML = `
                <p>Проверка статуса...</p>
                <div class="loading-spinner small"></div>
            `;
            
            try {
                const prediction = await PredictionAPI.getPrediction(predictionId);
                // Перезагружаем всю историю для обновления данных
                this.loadPredictionHistory();
            } catch (error) {
                console.error('Ошибка при проверке статуса:', error);
                event.target.parentNode.innerHTML = `
                    <p class="error">Ошибка при проверке статуса</p>
                    <button class="btn btn-sm btn-primary check-status" data-id="${predictionId}">Повторить</button>
                `;
                
                // Заново добавляем обработчик
                setTimeout(() => {
                    const newButton = event.target.parentNode.querySelector('.check-status');
                    if (newButton) {
                        newButton.addEventListener('click', this.handleCheckStatusClick.bind(this));
                    }
                }, 100);
            }
        }
    }
    
    /**
     * Загружает текущий баланс пользователя
     */
    async loadBalance() {
        if (!this.auth.isLoggedIn()) {
            return;
        }
        
        try {
            const balance = await BalanceAPI.getBalance();
            
            if (balance && balance.balance !== undefined) {
                this.currentBalance.textContent = balance.balance.toFixed(2);
            } else if (balance && balance.amount !== undefined) {
                this.currentBalance.textContent = balance.amount.toFixed(2);
            } else {
                throw new Error('Неверный формат данных баланса');
            }
        } catch (error) {
            console.error('Ошибка при загрузке баланса:', error);
            
            // Если произошла ошибка Internal Server Error, попробуем загрузить еще раз через некоторое время
            if (error.message && error.message.includes('Internal Server Error')) {
                this.currentBalance.innerHTML = `<span class="error">Загрузка баланса...</span>`;
                setTimeout(() => this.loadBalance(), 3000);
            } else {
                this.currentBalance.innerHTML = `<span class="error">Ошибка: ${error.message}</span>`;
            }
        }
    }
    
    /**
     * Обработчик формы пополнения баланса
     * @param {Event} event - Событие отправки формы
     */
    async handleTopUp(event) {
        event.preventDefault();
        
        if (!this.auth.isLoggedIn()) {
            this.auth.showLoginModal();
            return;
        }
        
        const amount = parseFloat(this.topupAmount.value);
        
        if (isNaN(amount) || amount <= 0) {
            this.topupError.textContent = 'Пожалуйста, введите корректную сумму пополнения';
            this.topupError.classList.remove('hidden');
            this.topupResult.classList.add('hidden');
            return;
        }
        
        try {
            this.topupError.classList.add('hidden');
            this.topupResult.classList.add('hidden');
            
            // Пополняем баланс
            const result = await BalanceAPI.topUpBalance(amount);
            
            // Отображаем результат
            this.previousBalance.textContent = result.previous_balance.toFixed(2);
            this.newBalance.textContent = result.current_balance.toFixed(2);
            this.currentBalance.textContent = result.current_balance.toFixed(2);
            
            this.topupResult.classList.remove('hidden');
            
            // Очищаем форму
            this.topupForm.reset();
            this.topupAmount.value = 10;
        } catch (error) {
            this.topupError.textContent = error.message || 'Ошибка при пополнении баланса';
            this.topupError.classList.remove('hidden');
            console.error('Ошибка при пополнении баланса:', error);
        }
    }
}

// Инициализация приложения после загрузки DOM
document.addEventListener('DOMContentLoaded', () => {
    const app = new App();
}); 