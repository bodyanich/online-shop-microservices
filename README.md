# 🚀 Швидкий запуск системи

## Передумови

- Docker Desktop 24+ встановлено
- Git встановлено
- 8 GB RAM вільно
- Порти вільні: 5432, 5433, 5672, 8001, 8002, 8003, 9090, 3000, 15672

---

## Крок 1: Клонування та підготовка

```bash
# Клонуй репозиторій
git clone <repository-url>
cd online-shop-microservices

# Створи папку для Prometheus конфігурації (якщо не існує)
mkdir -p prometheus
```

---

## Крок 2: Створення .env файлів (опціонально)

Сервіси працюють з дефолтними значеннями, але можеш створити .env файли:

```bash
# Product Service
cp product-service/.env.example product-service/.env

# Order Service
cp order-service/.env.example order-service/.env

# Notification Service
cp notification-service/.env.example notification-service/.env
```

---

## Крок 3: Запуск всієї системи

```bash
# Запуск у фоновому режимі
docker-compose up -d

# Або з логами (для дебагу)
docker-compose up
```

**Перший запуск займе 3-5 хвилин** (побудова Docker images).

---

## Крок 4: Перевірка статусу

```bash
docker-compose ps
```

**Очікуваний результат:**
```
NAME                    STATUS              PORTS
postgres-products       Up (healthy)        0.0.0.0:5432->5432/tcp
postgres-orders         Up (healthy)        0.0.0.0:5433->5432/tcp
rabbitmq                Up (healthy)        0.0.0.0:5672->5672/tcp, 0.0.0.0:15672->15672/tcp
product-service         Up                  0.0.0.0:8001->8000/tcp
order-service           Up                  0.0.0.0:8002->8000/tcp
notification-service    Up                  0.0.0.0:8003->8000/tcp
prometheus              Up                  0.0.0.0:9090->9090/tcp
grafana                 Up                  0.0.0.0:3000->3000/tcp
```

---

## Крок 5: Перевірка здоров'я сервісів

```bash
# Product Service
curl http://localhost:8001/health

# Order Service
curl http://localhost:8002/health

# Notification Service
curl http://localhost:8003/health
```

---

## Крок 6: Тестування системи

### 1. Додати товар (Product Service)

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

**Очікувана відповідь:**
```json
{
  "id": 1,
  "name": "Ноутбук Lenovo ThinkPad",
  "price": 25999.99,
  "stock": 10,
  ...
}
```

### 2. Переглянути товари

```bash
curl http://localhost:8001/products
```

### 3. Створити замовлення (Order Service)

```bash
curl -X POST http://localhost:8002/orders \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": 1,
    "quantity": 2,
    "customer_email": "customer@example.com"
  }'
```

**Що відбувається:**
1. ✅ Order Service викликає Product Service (перевіряє товар)
2. ✅ Order Service перевіряє stock >= quantity
3. ✅ Order Service зберігає замовлення в БД
4. ✅ Order Service публікує подію `OrderCreated` в RabbitMQ
5. ✅ Product Service отримує подію і зменшує stock (10 → 8)
6. ✅ Notification Service отримує подію і "надсилає" email (console)

### 4. Перевірити залишки оновлено

```bash
curl http://localhost:8001/products/1
```

**Очікується:** `"stock": 8` (було 10, замовили 2)

### 5. Переглянути логи Notification Service

```bash
docker-compose logs notification-service
```

**Очікується:**
```
📧 EMAIL NOTIFICATION (Console Mode)
To: customer@example.com
Subject: Order #1 Created Successfully
...
```

---

## Крок 7: Доступ до інтерфейсів

| Сервіс | URL | Credentials |
|--------|-----|-------------|
| **Product Service API** | http://localhost:8001/docs | - |
| **Order Service API** | http://localhost:8002/docs | - |
| **Notification Service** | http://localhost:8003/health | - |
| **RabbitMQ Management** | http://localhost:15672 | guest / guest |
| **Prometheus** | http://localhost:9090 | - |
| **Grafana** | http://localhost:3000 | admin / admin |

---

## Крок 8: Перегляд метрик (Prometheus)

1. Відкрий http://localhost:9090
2. Введи запит:
   ```promql
   rate(http_requests_total[1m])
   ```
3. Натисни "Execute"
4. Перейди на вкладку "Graph"

**Інші корисні запити:**
```promql
# HTTP requests per second
rate(http_requests_total[1m])

# Average response time
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[1m])
```

---

## Крок 9: Grafana Dashboard

1. Відкрий http://localhost:3000
2. Login: `admin` / Password: `admin`
3. Додай Data Source:
   - Configuration → Data Sources → Add data source
   - Вибери Prometheus
   - URL: `http://prometheus:9090`
   - Save & Test
4. Створи Dashboard або імпортуй готовий

---

## Перегляд логів

```bash
# Всі сервіси
docker-compose logs -f

# Конкретний сервіс
docker-compose logs -f product-service
docker-compose logs -f order-service
docker-compose logs -f notification-service

# Останні 100 рядків
docker-compose logs --tail=100 order-service
```

---

## RabbitMQ Management UI

1. Відкрий http://localhost:15672
2. Login: `guest` / Password: `guest`
3. Перейди на вкладку **Queues**
4. Побачиш:
   - `order.created.product`
   - `order.created.notification`

**Тут можна:**
- Переглянути кількість повідомлень
- Бачити consumers
- Manually publish/get messages

---

## Зупинка системи

```bash
# Зупинити всі сервіси (зберегти дані)
docker-compose down

# Зупинити і видалити volumes (ВИДАЛИТЬ ВСІ ДАНІ)
docker-compose down -v
```

---

## Перезапуск окремого сервісу

```bash
# Перезапустити сервіс
docker-compose restart product-service

# Пересобрати і перезапустити
docker-compose up -d --build product-service
```

---

## Масштабування

```bash
# Запустити 3 екземпляри Order Service
docker-compose up -d --scale order-service=3

# Перевірити
docker-compose ps
```

---

## Troubleshooting

### Проблема: Контейнер не стартує

```bash
# Перевірити логи
docker-compose logs <service-name>

# Перезапустити
docker-compose restart <service-name>

# Пересобрати з нуля
docker-compose build --no-cache <service-name>
docker-compose up -d <service-name>
```

### Проблема: Port already in use

```bash
# Linux/Mac
sudo lsof -i :8001
kill -9 <PID>

# Windows
netstat -ano | findstr :8001
taskkill /PID <PID> /F

# Або змінити порт у docker-compose.yml
ports:
  - "8011:8000"  # Замість 8001
```

### Проблема: База даних недоступна

```bash
# Підключитися до контейнера PostgreSQL
docker exec -it postgres-products psql -U user -d products_db

# Перевірити таблиці
\dt

# Вийти
\q
```

### Проблема: RabbitMQ events не обробляються

```bash
# Перевірити що consumer запущений
docker-compose logs product-service | grep "Waiting for messages"

# Перевірити черги в RabbitMQ UI
# http://localhost:15672/#/queues

# Перезапустити consumer
docker-compose restart product-service
```

---

## База даних: корисні команди

### Product Service DB

```bash
# Підключитися
docker exec -it postgres-products psql -U user -d products_db

# Переглянути товари
SELECT * FROM products;

# Переглянути оброблені події
SELECT * FROM processed_events;
```

### Order Service DB

```bash
# Підключитися
docker exec -it postgres-orders psql -U user -d orders_db

# Переглянути замовлення
SELECT * FROM orders;

# Замовлення з статусом pending
SELECT * FROM orders WHERE status = 'pending';
```

---

## Корисні команди

```bash
# Rebuild усіх images
docker-compose build --no-cache

# Видалити всі volumes
docker-compose down -v

# Видалити orphan containers
docker-compose down --remove-orphans

# Перевірити використання ресурсів
docker stats

# Очистити Docker
docker system prune -a
```

---