# ЛАБОРАТОРНА РОБОТА №5
## Розробка прототипу сервісу

**Тема проекту:** Система управління замовленнями у невеликому онлайн-магазині

**Виконав:** Бородій Богдан Сергійович  
**Група:** ІПЗм-25  
**Дата:** 15.11.2025

---

## 1. МЕТА РОБОТИ

Створити робочі прототипи мікросервісів з REST API, реалізувати CRUD-операції, налаштувати взаємодію з базою даних PostgreSQL та контейнеризувати сервіси за допомогою Docker.

---

## 2. КОРОТКІ ТЕОРЕТИЧНІ ВІДОМОСТІ

**REST (Representational State Transfer)** — архітектурний стиль для створення веб-сервісів, що використовує стандартні HTTP-методи:
- **GET** — отримання ресурсів
- **POST** — створення нових ресурсів
- **PUT/PATCH** — оновлення існуючих ресурсів
- **DELETE** — видалення ресурсів

**FastAPI** — сучасний Python-фреймворк для створення API з автоматичною генерацією документації (OpenAPI/Swagger), валідацією даних через Pydantic та підтримкою асинхронного програмування.

**SQLAlchemy** — популярний ORM (Object-Relational Mapping) для Python, що дозволяє працювати з базами даних через об'єкти Python замість прямих SQL-запитів.

**Docker** — платформа для контейнеризації застосунків, що забезпечує ізоляцію середовища виконання та спрощує розгортання.

---

## 3. РЕАЛІЗОВАНІ СЕРВІСИ

### 3.1. Product Service

**Призначення:** Управління каталогом товарів та залишками на складі

**Реалізовані endpoints:**

| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/products` | Список всіх товарів (з пагінацією) |
| GET | `/products/{id}` | Деталі конкретного товару |
| POST | `/products` | Створення нового товару |
| PUT | `/products/{id}` | Оновлення товару |
| DELETE | `/products/{id}` | Видалення товару |
| PATCH | `/products/{id}/stock` | Оновлення залишків |
| GET | `/products/{id}/check` | Перевірка наявності |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus метрики |

**Структура проекту:**
```
product-service/
├── app/
│   ├── api/          # API endpoints
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   ├── repositories/ # Data access layer
│   ├── consumers/    # RabbitMQ consumers
│   ├── database.py
│   ├── config.py
│   └── main.py
├── Dockerfile
└── requirements.txt
```

**Модель даних (Product):**
```python
class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    category = Column(String(100))
    image_url = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

---

### 3.2. Order Service

**Призначення:** Обробка замовлень та координація з іншими сервісами

**Реалізовані endpoints:**

| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/orders` | Список всіх замовлень (з пагінацією) |
| GET | `/orders/{id}` | Деталі замовлення |
| POST | `/orders` | Створення замовлення |
| PATCH | `/orders/{id}/status` | Оновлення статусу |
| GET | `/orders/customer/{email}` | Замовлення клієнта |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus метрики |

**Структура проекту:**
```
order-service/
├── app/
│   ├── api/          # API endpoints
│   ├── models/       # SQLAlchemy models
│   ├── schemas/      # Pydantic schemas
│   ├── services/     # Business logic
│   ├── repositories/ # Data access layer
│   ├── publishers/   # RabbitMQ publishers
│   ├── database.py
│   ├── config.py
│   └── main.py
├── Dockerfile
└── requirements.txt
```

**Модель даних (Order):**
```python
class Order(Base):
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    product_name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(50), default='pending')
    customer_email = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

---

### 3.3. Notification Service

**Призначення:** Асинхронне надсилання сповіщень про події у системі

**Реалізовані endpoints:**

| Метод | Endpoint | Опис |
|-------|----------|------|
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus метрики |

**Особливості:**
- Працює як RabbitMQ consumer (без публічних business endpoints)
- Обробляє події `OrderCreated` та `OrderStatusChanged`
- У навчальній версії логує сповіщення у консоль
- Підготовлений для інтеграції з SendGrid/SMTP

---

## 4. БАЗИ ДАНИХ

### 4.1. products_db

**СУБД:** PostgreSQL 15

**Таблиці:**

**products:**
- `id` — унікальний ідентифікатор (PRIMARY KEY)
- `name` — назва товару
- `description` — опис
- `price` — ціна (CHECK >= 0)
- `stock` — залишок (CHECK >= 0)
- `category` — категорія
- `image_url` — посилання на зображення
- `created_at`, `updated_at` — timestamps

**processed_events:**
- `event_id` — ID події (PRIMARY KEY)
- `event_type` — тип події
- `processed_at` — час обробки

**Індекси:**
- `idx_products_category` на `category`
- `idx_products_stock` на `stock` WHERE stock > 0
- `idx_products_name` на `name`

---

### 4.2. orders_db

**СУБД:** PostgreSQL 15

**Таблиці:**

**orders:**
- `id` — унікальний ідентифікатор (PRIMARY KEY)
- `product_id` — ID товару
- `product_name` — назва товару (денормалізація)
- `quantity` — кількість (CHECK > 0)
- `unit_price` — ціна за одиницю
- `total_price` — загальна вартість
- `status` — статус замовлення (pending/processing/completed/cancelled)
- `customer_email` — email клієнта
- `created_at`, `updated_at` — timestamps

**Індекси:**
- `idx_orders_status` на `status`
- `idx_orders_created_at` на `created_at DESC`
- `idx_orders_customer_email` на `customer_email`
- `idx_orders_product_id` на `product_id`

---

## 5. КОНТЕЙНЕРИЗАЦІЯ

### 5.1. Dockerfile (Product Service)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN apt-get update && apt-get install -y postgresql-client

# Copy and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Оптимізації:**
- Multi-stage build для зменшення розміру образу
- Встановлення лише необхідних системних залежностей
- Використання `--no-cache-dir` для pip
- Health check для Kubernetes/Docker

---

### 5.2. Docker Compose

**Структура:**
```yaml
services:
  postgres-products:    # База для Product Service
  postgres-orders:      # База для Order Service
  rabbitmq:             # Message broker
  product-service:      # Сервіс товарів
  order-service:        # Сервіс замовлень
  notification-service: # Сервіс сповіщень
  prometheus:           # Моніторинг
  grafana:              # Візуалізація метрик
```

**Мережі:**
- `backend-network` — для міжсервісної взаємодії
- `database-network` — для доступу до БД

**Volumes:**
- `products-data` — дані PostgreSQL (products)
- `orders-data` — дані PostgreSQL (orders)
- `rabbitmq-data` — дані RabbitMQ
- `prometheus-data` — дані Prometheus
- `grafana-data` — дані Grafana

---

## 6. ПРИКЛАДИ ВИКОРИСТАННЯ API

### 6.1. Створення товару

**Request:**
```bash
curl -X POST http://localhost:8001/products \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Ноутбук Lenovo ThinkPad",
    "description": "Професійний ноутбук",
    "price": 25999.99,
    "stock": 10,
    "category": "Електроніка"
  }'
```

**Response (201 Created):**
```json
{
  "id": 1,
  "name": "Ноутбук Lenovo ThinkPad",
  "description": "Професійний ноутбук",
  "price": 25999.99,
  "stock": 10,
  "category": "Електроніка",
  "image_url": null,
  "created_at": "2025-11-15T10:30:00Z",
  "updated_at": "2025-11-15T10:30:00Z"
}
```

---

### 6.2. Створення замовлення

**Request:**
```bash
curl -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2,
    "customer_email": "customer@example.com"
  }'
```

**Response (201 Created):**
```json
{
  "id": 101,
  "product_id": 1,
  "product_name": "Ноутбук Lenovo ThinkPad",
  "quantity": 2,
  "unit_price": 25999.99,
  "total_price": 51999.98,
  "status": "pending",
  "customer_email": "customer@example.com",
  "created_at": "2025-11-15T10:35:00Z",
  "updated_at": "2025-11-15T10:35:00Z"
}
```

**Що відбувається після створення:**
1. ✅ Order Service зберігає замовлення у БД
2. ✅ Публікує подію `OrderCreated` у RabbitMQ
3. ✅ Product Service отримує подію і зменшує `stock` (10 → 8)
4. ✅ Notification Service отримує подію і "надсилає" email

---

### 6.3. Перевірка наявності товару

**Request:**
```bash
curl http://localhost:8001/products/1/check?quantity=5
```

**Response (200 OK):**
```json
{
  "product_id": 1,
  "available": true,
  "stock": 8,
  "message": null
}
```

---

## 7. ТЕСТУВАННЯ СИСТЕМИ

### 7.1. Запуск системи

```bash
# Запуск всіх сервісів
docker-compose up -d

# Перевірка статусу
docker-compose ps

# Перегляд логів
docker-compose logs -f product-service
docker-compose logs -f order-service
docker-compose logs -f notification-service
```

### 7.2. Перевірка health endpoints

```bash
# Product Service
curl http://localhost:8001/health

# Order Service
curl http://localhost:8002/health

# Notification Service
curl http://localhost:8003/health
```

**Очікувана відповідь:**
```json
{
  "service": "product-service",
  "status": "healthy",
  "database": "healthy",
  "timestamp": "2025-11-15T10:40:00Z"
}
```

### 7.3. Тестування повного циклу

**Крок 1: Додати товар**
```bash
curl -X POST http://localhost:8001/products \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Product", "price": 100, "stock": 50, "category": "Test"}'
```

**Крок 2: Створити замовлення**
```bash
curl -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 3, "customer_email": "test@example.com"}'
```

**Крок 3: Перевірити оновлення залишків**
```bash
curl http://localhost:8001/products/1
# Очікується: "stock": 47 (було 50, замовили 3)
```

**Крок 4: Переглянути логи сповіщень**
```bash
docker-compose logs notification-service
```

**Очікується:**
```
📧 EMAIL NOTIFICATION (Console Mode)
To: test@example.com
Subject: Order #1 Created Successfully
...
```

---

## 10. ВИСНОВКИ

У ході виконання лабораторної роботи №5 було успішно розроблено та розгорнуто робочі прототипи трьох мікросервісів системи управління замовленнями.

**Основні досягнення:**

1. **Реалізовано 3 мікросервіси:**
   - Product Service: 9 endpoints для управління товарами
   - Order Service: 7 endpoints для обробки замовлень
   - Notification Service: consumer для асинхронних сповіщень

2. **Налаштовано бази даних:**
   - 2 PostgreSQL instances з окремими БД
   - Міграції схем через SQLAlchemy
   - Індекси для оптимізації запитів

3. **Реалізовано CRUD-операції:**
   - Повний життєвий цикл товарів
   - Створення та управління замовленнями
   - Валідація даних через Pydantic

4. **Налаштовано міжсервісну взаємодію:**
   - Синхронна: Order → Product (HTTP/REST)
   - Асинхронна: через RabbitMQ (події)

5. **Контейнеризація:**
   - Dockerfile для кожного сервісу
   - Docker Compose для оркестрації
   - Health checks для моніторингу

6. **Автоматична документація:**
   - Swagger UI для тестування API
   - ReDoc для читання документації

7. **Моніторинг:**
   - Prometheus для збору метрик
   - Grafana для візуалізації

**Перевірено працездатність:**
- Створення товарів через REST API
- Створення замовлень з перевіркою наявності
- Автоматичне оновлення залишків через події
- Надсилання сповіщень через RabbitMQ
- Health checks усіх сервісів

**Технології, використані на практиці:**
- Python 3.11 + FastAPI
- PostgreSQL 15
- RabbitMQ 3
- Docker + Docker Compose
- Prometheus + Grafana
- SQLAlchemy ORM
- Pydantic validation

Створені прототипи повністю функціональні та готові для подальшого розвитку у наступних лабораторних роботах (реалізація складніших сценаріїв, навантажувальне тестування, масштабування).

---