# ML Service - Сервис для задач машинного обучения

Объектная модель сервиса для задач машинного обучения. В сервисе пользователи могут запускать различные ML задачи, потребляя кредиты со своего баланса.

## Структура объектной модели

### Базовые сущности

- `Entity` - абстрактный базовый класс для всех сущностей
- `MLTask` - абстрактный класс для задач ML
- `UserRole` - абстрактный класс для ролей пользователей

### Пользователи и роли

- `User` - модель пользователя системы
- `RegularUserRole` - роль обычного пользователя системы
- `AdminRole` - роль администратора с расширенными полномочиями

### Задачи ML

- `MLJob` - модель выполняемой работы по задаче ML
- `EmotionClassificationTask` - пример конкретной задачи ML (классификация эмоций)

### Транзакции

- `Transaction` - модель транзакции (пополнение/списание кредитов)
- `TopUpRequest` - модель запроса на пополнение баланса (требует модерации администратором)
- `TransactionType` и `TransactionStatus` - перечисления для типов и статусов транзакций

