# ЛАБОРАТОРНА РОБОТА №3
## Моделювання взаємодії сервісів

**Тема проекту:** Система управління замовленнями у невеликому онлайн-магазині

**Виконав:** [Ваше ім'я]  
**Група:** [Ваша група]  
**Дата:** 15.11.2025

---

## 1. МЕТА РОБОТИ

Змоделювати потоки даних у розподіленій системі, описати послідовність взаємодії між мікросервісами для конкретних use cases, визначити типи міжсервісної комунікації та побудувати діаграми послідовності (Sequence Diagram) та розгортання (Deployment Diagram).

---

## 2. КОРОТКІ ТЕОРЕТИЧНІ ВІДОМОСТІ

### 2.1. Види міжсервісної взаємодії

У розподілених програмних системах мікросервіси взаємодіють між собою двома основними способами:

#### Синхронна взаємодія
Сервіс викликає інший сервіс і чекає на відповідь. Найпоширеніші протоколи:
- **REST (HTTP/HTTPS)** - використовує стандартні HTTP-методи (GET, POST, PUT, DELETE)
- **gRPC** - високопродуктивний протокол на основі HTTP/2 з бінарною серіалізацією

**Переваги:**
- Простота реалізації
- Негайна відповідь
- Легко дебажити

**Недоліки:**
- Жорстка зв'язаність (tight coupling)
- Каскадні відмови
- Блокування при очікуванні відповіді

#### Асинхронна взаємодія
Сервіс надсилає повідомлення або подію, не очікуючи негайної відповіді. Реалізується через брокери повідомлень:
- **RabbitMQ** - класичний брокер з чергами повідомлень
- **Apache Kafka** - розподілена платформа для потокової обробки подій
- **NATS** - легковаговий брокер повідомлень

**Переваги:**
- Слабка зв'язаність (loose coupling)
- Висока відмовостійкість
- Можливість масштабування споживачів

**Недоліки:**
- Складність налагодження
- Eventual consistency
- Потрібен додатковий компонент (брокер)

### 2.2. Патерни комунікації

#### Request/Response (REST)
Клієнт надсилає запит і очікує відповідь.
```
Client → Service: HTTP Request
Service → Client: HTTP Response
```

#### Publish/Subscribe (Events)
Видавець публікує подію, підписники її обробляють.
```
Publisher → Broker: Event
Broker → Subscriber 1: Event
Broker → Subscriber 2: Event
```

#### API Composition
Один сервіс агрегує дані з кількох інших сервісів.
```
API Gateway → Service A: Request
API Gateway → Service B: Request
API Gateway → Client: Aggregated Response
```

### 2.3. Діаграма послідовності (Sequence Diagram)

Sequence Diagram показує:
- Учасників взаємодії (actors, services)
- Порядок повідомлень у часі
- Синхронні/асинхронні виклики
- Життєві цикли об'єктів
- Умовну логіку (alt, opt, loop)

### 2.4. Діаграма розгортання (Deployment Diagram)

Deployment Diagram показує:
- Фізичні вузли (nodes) - сервери, контейнери
- Програмні компоненти на вузлах
- Мережеві з'єднання
- Протоколи комунікації
- Конфігурацію інфраструктури

---

## 3. ОБРАНИЙ СЦЕНАРІЙ: СТВОРЕННЯ ЗАМОВЛЕННЯ

### 3.1. Опис use case

**Use Case:** Покупець створює замовлення на товар

**Актори:**
- **Покупець (Customer)** - ініціює створення замовлення
- **Order Service** - координує процес створення замовлення
- **Product Service** - надає інформацію про товар та оновлює залишки
- **Notification Service** - надсилає сповіщення про створене замовлення
- **RabbitMQ** - транспортує події між сервісами
- **PostgreSQL (orders_db)** - зберігає замовлення
- **PostgreSQL (products_db)** - зберігає товари

**Передумови:**
1. Товар існує в каталозі Product Service
2. Товар має достатню кількість на складі (stock >= quantity)
3. Всі сервіси доступні та працюють

**Основний потік:**
1. Покупець надсилає HTTP POST запит до Order Service з `product_id` та `quantity`
2. Order Service валідує вхідні дані
3. Order Service синхронно викликає Product Service для отримання інформації про товар
4. Product Service повертає дані товару (назва, ціна, залишок)
5. Order Service перевіряє достатність товару на складі
6. Order Service розраховує загальну вартість замовлення
7. Order Service зберігає замовлення в БД orders_db
8. Order Service публікує подію `OrderCreated` у RabbitMQ
9. Order Service повертає відповідь покупцю (201 Created)
10. Product Service отримує подію `OrderCreated` з RabbitMQ
11. Product Service зменшує залишок товару в products_db
12. Notification Service отримує подію `OrderCreated` з RabbitMQ
13. Notification Service надсилає email-сповіщення покупцю

**Альтернативні потоки:**

**A1. Товар не знайдено:**
- Крок 3: Product Service повертає 404 Not Found
- Order Service повертає 400 Bad Request з повідомленням "Product not found"
- Замовлення не створюється

**A2. Недостатньо товару на складі:**
- Крок 5: stock < quantity
- Order Service повертає 409 Conflict з повідомленням "Insufficient stock"
- Замовлення не створюється

**A3. Product Service недоступний:**
- Крок 3: Timeout або Connection Error
- Order Service повторює запит (retry) до 3 разів
- Якщо всі спроби невдалі: повертає 503 Service Unavailable
- Замовлення не створюється

**A4. RabbitMQ недоступний:**
- Крок 8: Не вдається опублікувати подію
- Order Service зберігає подію в локальній таблиці outbox
- Фоновий процес пізніше публікує збережені події
- Покупець отримує підтвердження замовлення

**Постумови (успішне виконання):**
1. Замовлення збережено в orders_db зі статусом "pending"
2. Залишок товару зменшено в products_db
3. Покупець отримав email-сповіщення
4. Події записано в логи для аудиту

**Метрики:**
- Середній час виконання: 300-500 мс
- Успішність: 98%+
- Затримка публікації події: < 100 мс
- Час обробки події Product Service: < 200 мс
- Час обробки події Notification Service: < 500 мс

---

## 4. SEQUENCE DIAGRAM: СТВОРЕННЯ ЗАМОВЛЕННЯ (УСПІШНИЙ ПОТІК)

### 4.1. Опис діаграми

Діаграма послідовності показує покроковий процес створення замовлення від початкового запиту покупця до фінального надсилання сповіщення.

**Учасники:**
1. `Customer` - покупець (клієнт)
2. `Order Service` - сервіс замовлень
3. `orders_db` - база даних замовлень
4. `Product Service` - сервіс товарів
5. `products_db` - база даних товарів
6. `RabbitMQ` - брокер повідомлень
7. `Notification Service` - сервіс сповіщень

**Типи стрілок:**
- `→` синхронний виклик (чекаємо відповіді)
- `-->` асинхронний виклик або повернення результату
- `->>` публікація події

### 4.2. PlantUML код діаграми

```plantuml
@startuml Sequence_Diagram_Create_Order_Success

autonumber
skinparam sequenceArrowThickness 2
skinparam roundcorner 20
skinparam maxmessagesize 200

title Sequence Diagram - Створення замовлення (успішний сценарій)

actor Customer as customer
participant "Order Service" as order_service
database "orders_db\n(PostgreSQL)" as orders_db
participant "Product Service" as product_service
database "products_db\n(PostgreSQL)" as products_db
queue "RabbitMQ" as rabbitmq
participant "Notification Service" as notification_service

== Валідація та перевірка товару ==

customer -> order_service: POST /orders\n{product_id: 1, quantity: 2}
activate order_service

order_service -> order_service: Валідація вхідних даних\n(quantity > 0)

order_service -> product_service: GET /products/1\n(Синхронний HTTP запит)
activate product_service

product_service -> products_db: SELECT * FROM products\nWHERE id = 1
activate products_db
products_db --> product_service: {id: 1, name: "Laptop",\nprice: 25999.99, stock: 15}
deactivate products_db

product_service --> order_service: 200 OK\n{id: 1, name: "Laptop",\nprice: 25999.99, stock: 15}
deactivate product_service

order_service -> order_service: Перевірка наявності:\nstock (15) >= quantity (2) ✓

order_service -> order_service: Розрахунок вартості:\ntotal = 25999.99 * 2 = 51999.98

== Збереження замовлення ==

order_service -> orders_db: INSERT INTO orders\n(product_id, quantity,\ntotal_price, status)
activate orders_db
orders_db --> order_service: Order created\n{id: 101}
deactivate orders_db

== Публікація події ==

order_service -> rabbitmq: Publish OrderCreated\n{order_id: 101,\nproduct_id: 1,\nquantity: 2}
activate rabbitmq
note right of rabbitmq
  Exchange: orders_exchange
  Routing Key: order.created
  Delivery Mode: Persistent
end note
rabbitmq --> order_service: ACK (подія прийнята)
deactivate rabbitmq

order_service --> customer: 201 Created\n{id: 101, product_id: 1,\nquantity: 2,\ntotal_price: 51999.98,\nstatus: "pending"}
deactivate order_service

== Асинхронна обробка події (Product Service) ==

rabbitmq ->> product_service: Deliver OrderCreated\n{order_id: 101,\nproduct_id: 1, quantity: 2}
activate product_service

product_service -> products_db: UPDATE products\nSET stock = stock - 2\nWHERE id = 1
activate products_db
products_db --> product_service: Updated (stock: 15 → 13)
deactivate products_db

product_service -> rabbitmq: ACK (подія оброблена)
deactivate product_service

== Асинхронна обробка події (Notification Service) ==

rabbitmq ->> notification_service: Deliver OrderCreated\n{order_id: 101,\nproduct_id: 1,\ncustomer_email: "user@example.com"}
activate notification_service

notification_service -> notification_service: Формування повідомлення:\n"Order #101 created\nTotal: 51999.98 UAH"

notification_service -> notification_service: Надсилання email\n(simulate)
note right of notification_service
  У навчальному проекті:
  print("Email sent to user@example.com")
  
  У продакшні:
  SendGrid / AWS SES
end note

notification_service -> rabbitmq: ACK (подія оброблена)
deactivate notification_service

@enduml
```

### 4.3. Аналіз діаграми

**Синхронні операції (блокуючі):**
1. **Customer → Order Service** (кроки 1-13)
   - Покупець чекає на підтвердження замовлення
   - Час відповіді: ~300-500 мс

2. **Order Service → Product Service** (кроки 4-7)
   - Order Service блокується до отримання відповіді
   - Час відповіді: ~50-100 мс
   - Критична залежність (якщо Product Service недоступний, замовлення не створюється)

**Асинхронні операції (неблокуючі):**
1. **Order Service → RabbitMQ** (крок 10)
   - Order Service не чекає на обробку події
   - Просто публікує та отримує ACK від брокера
   - Час: ~10-20 мс

2. **RabbitMQ → Product Service** (кроки 14-18)
   - Обробляється в фоновому режимі
   - Не впливає на час відповіді клієнту
   - Eventual consistency: залишок оновиться через 100-200 мс

3. **RabbitMQ → Notification Service** (кроки 19-24)
   - Повністю незалежна обробка
   - Навіть якщо email не відправиться, замовлення вже створено

**Критичні моменти:**

🔴 **Single Point of Failure:**
- Product Service на кроці 4 - якщо недоступний, весь процес зупиняється
- **Рішення:** Додати retry logic та circuit breaker

🟡 **Eventual Consistency:**
- Між кроками 13 та 18 існує часовий проміжок, коли замовлення створено, але залишок ще не оновлений
- **Рішення:** Прийнятно для даної бізнес-логіки

🟢 **Відмовостійкість:**
- Якщо Notification Service падає, замовлення все одно створюється
- Повідомлення залишається в черзі RabbitMQ до відновлення сервісу

---

## 5. SEQUENCE DIAGRAM: АЛЬТЕРНАТИВНІ ПОТОКИ

### 5.1. Недостатньо товару на складі

```plantuml
@startuml Sequence_Diagram_Insufficient_Stock

autonumber
skinparam sequenceArrowThickness 2
skinparam roundcorner 20

title Sequence Diagram - Недостатньо товару на складі

actor Customer as customer
participant "Order Service" as order_service
participant "Product Service" as product_service
database "products_db" as products_db

customer -> order_service: POST /orders\n{product_id: 1, quantity: 20}
activate order_service

order_service -> product_service: GET /products/1
activate product_service

product_service -> products_db: SELECT * FROM products\nWHERE id = 1
activate products_db
products_db --> product_service: {id: 1, stock: 5}
deactivate products_db

product_service --> order_service: 200 OK\n{stock: 5}
deactivate product_service

order_service -> order_service: Перевірка:\nstock (5) < quantity (20) ✗

order_service --> customer: 409 Conflict\n{"error": "Insufficient stock",\n"available": 5,\n"requested": 20}
deactivate order_service

note right of customer
  Замовлення НЕ створено
  Події НЕ опубліковано
  База даних НЕ змінена
end note

@enduml
```

### 5.2. Product Service недоступний (з retry)

```plantuml
@startuml Sequence_Diagram_Service_Unavailable

autonumber
skinparam sequenceArrowThickness 2
skinparam roundcorner 20

title Sequence Diagram - Product Service недоступний (з retry механізмом)

actor Customer as customer
participant "Order Service" as order_service
participant "Product Service" as product_service

customer -> order_service: POST /orders\n{product_id: 1, quantity: 2}
activate order_service

order_service -> product_service: GET /products/1\n(Спроба #1)
activate product_service
product_service --> order_service: ❌ Timeout / Connection Error
deactivate product_service

note right of order_service
  Retry after 1 second
end note

order_service -> order_service: Wait 1 sec

order_service -> product_service: GET /products/1\n(Спроба #2)
activate product_service
product_service --> order_service: ❌ Timeout / Connection Error
deactivate product_service

note right of order_service
  Retry after 2 seconds
end note

order_service -> order_service: Wait 2 sec

order_service -> product_service: GET /products/1\n(Спроба #3)
activate product_service
product_service --> order_service: ❌ Timeout / Connection Error
deactivate product_service

note right of order_service
  Max retries reached
  Circuit breaker OPEN
end note

order_service --> customer: 503 Service Unavailable\n{"error": "Product Service unavailable",\n"message": "Please try again later"}
deactivate order_service

note right of customer
  Замовлення НЕ створено
  Клієнт може повторити пізніше
  Альтернатива: зберегти у outbox
  для відкладеної обробки
end note

@enduml
```

---

## 6. DEPLOYMENT DIAGRAM

### 6.1. Опис інфраструктури

Система розгортається у Docker контейнерах, керованих Docker Compose. Усі компоненти працюють у окремих контейнерах та взаємодіють через Docker networks.

**Мережеві сегменти:**
1. **frontend-network** - для клієнтських запитів (опціонально, для майбутнього веб-інтерфейсу)
2. **backend-network** - для міжсервісної взаємодії
3. **database-network** - для доступу до баз даних

**Порти:**
- Product Service: 8001
- Order Service: 8002
- Notification Service: 8003
- PostgreSQL (products): 5432
- PostgreSQL (orders): 5433
- RabbitMQ: 5672 (AMQP), 15672 (Management UI)
- Prometheus: 9090
- Grafana: 3000

### 6.2. PlantUML код Deployment Diagram

```plantuml
@startuml Deployment_Diagram

!define CONTAINER node

skinparam node {
    BackgroundColor LightBlue
    BorderColor Black
}

skinparam component {
    BackgroundColor LightYellow
    BorderColor Black
}

skinparam database {
    BackgroundColor LightGreen
    BorderColor Black
}

title Deployment Diagram - Docker Compose Infrastructure

cloud "Internet" {
    actor "Customer" as customer
    actor "Administrator" as admin
}

CONTAINER "Docker Host" {
    
    package "backend-network" {
        
        CONTAINER "product-service\n(Docker Container)" as ps_container {
            component "Product Service\nFastAPI:8000" as ps
            note right of ps
              Image: product-service:latest
              Port: 8001:8000
              Env: DATABASE_URL, RABBITMQ_URL
              Replicas: 1 (можна масштабувати)
            end note
        }
        
        CONTAINER "order-service\n(Docker Container)" as os_container {
            component "Order Service\nFastAPI:8000" as os
            note right of os
              Image: order-service:latest
              Port: 8002:8000
              Env: DATABASE_URL, RABBITMQ_URL,
                   PRODUCT_SERVICE_URL
              Replicas: 1 (можна масштабувати)
            end note
        }
        
        CONTAINER "notification-service\n(Docker Container)" as ns_container {
            component "Notification Service\nFastAPI:8000" as ns
            note right of ns
              Image: notification-service:latest
              Port: 8003:8000
              Env: RABBITMQ_URL
              Replicas: 1-3 (легко масштабується)
            end note
        }
        
        CONTAINER "rabbitmq\n(Docker Container)" as rabbitmq_container {
            component "RabbitMQ 3\nPort: 5672" as rabbitmq
            component "Management UI\nPort: 15672" as rabbitmq_ui
            note right of rabbitmq
              Image: rabbitmq:3-management
              Ports: 5672:5672, 15672:15672
              Volume: rabbitmq-data
              Persistent: true
            end note
        }
    }
    
    package "database-network" {
        
        CONTAINER "postgres-products\n(Docker Container)" as pg_products_container {
            database "PostgreSQL 15\nproducts_db\nPort: 5432" as pg_products
            note right of pg_products
              Image: postgres:15
              Port: 5432:5432
              Volume: products-data
              User: user / password
            end note
        }
        
        CONTAINER "postgres-orders\n(Docker Container)" as pg_orders_container {
            database "PostgreSQL 15\norders_db\nPort: 5432" as pg_orders
            note right of pg_orders
              Image: postgres:15
              Port: 5433:5432
              Volume: orders-data
              User: user / password
            end note
        }
    }
    
    package "monitoring-network" {
        
        CONTAINER "prometheus\n(Docker Container)" as prom_container {
            component "Prometheus\nPort: 9090" as prometheus
            note right of prometheus
              Image: prom/prometheus
              Port: 9090:9090
              Config: prometheus.yml
              Scrapes: /metrics endpoints
            end note
        }
        
        CONTAINER "grafana\n(Docker Container)" as grafana_container {
            component "Grafana\nPort: 3000" as grafana
            note right of grafana
              Image: grafana/grafana
              Port: 3000:3000
              Data Source: Prometheus
              Dashboards: preloaded
            end note
        }
    }
}

' External connections
customer -down-> os : HTTPS/JSON\nPOST /orders
admin -down-> ps : HTTPS/JSON\nCRUD /products

' Service to service (backend-network)
os -right-> ps : HTTP/JSON\nGET /products/{id}
os -down-> rabbitmq : AMQP\nPublish Events
rabbitmq -up-> ps : AMQP\nDeliver Events
rabbitmq -up-> ns : AMQP\nDeliver Events

' Service to database (database-network)
ps -down-> pg_products : SQL/TCP\nPort: 5432
os -down-> pg_orders : SQL/TCP\nPort: 5432

' Monitoring (monitoring-network)
ps -down-> prometheus : HTTP\n/metrics
os -down-> prometheus : HTTP\n/metrics
ns -down-> prometheus : HTTP\n/metrics
grafana -left-> prometheus : PromQL\nQuery Metrics

' Management UI
admin -down-> rabbitmq_ui : HTTP\nPort: 15672
admin -down-> grafana : HTTP\nPort: 3000

legend right
  **Docker Compose Configuration:**
  • Total Containers: 8
  • Networks: 3 (backend, database, monitoring)
  • Volumes: 4 (2x PostgreSQL, 1x RabbitMQ, 1x Grafana)
  • External Ports: 6
  
  **Deployment Commands:**
  docker-compose up -d
  docker-compose ps
  docker-compose logs -f
  docker-compose down
endlegend

@enduml
```

### 6.3. Docker Compose конфігурація (спрощена)

```yaml
version: '3.8'

services:
  postgres-products:
    image: postgres:15
    container_name: postgres-products
    environment:
      POSTGRES_DB: products_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - products-data:/var/lib/postgresql/data
    networks:
      - database-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  postgres-orders:
    image: postgres:15
    container_name: postgres-orders
    environment:
      POSTGRES_DB: orders_db
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5433:5432"
    volumes:
      - orders-data:/var/lib/postgresql/data
    networks:
      - database-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

  rabbitmq:
    image: rabbitmq:3-management
    container_name: rabbitmq
    ports:
      - "5672:5672"
      - "15672:15672"
    environment:
      RABBITMQ_DEFAULT_USER: guest
      RABBITMQ_DEFAULT_PASS: guest
    volumes:
      - rabbitmq-data:/var/lib/rabbitmq
    networks:
      - backend-network
    healthcheck:
      test: ["CMD", "rabbitmq-diagnostics", "ping"]
      interval: 30s
      timeout: 10s
      retries: 5

  product-service:
    build: ./product-service
    container_name: product-service
    ports:
      - "8001:8000"
    environment:
      DATABASE_URL: postgresql://user:password@postgres-products:5432/products_db
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      SERVICE_NAME: product-service
      LOG_LEVEL: INFO
    depends_on:
      postgres-products:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
    networks:
      - backend-network
      - database-network
    restart: unless-stopped

  order-service:
    build: ./order-service
    container_name: order-service
    ports:
      - "8002:8000"
    environment:
      DATABASE_URL: postgresql://user:password@postgres-orders:5432/orders_db
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      PRODUCT_SERVICE_URL: http://product-service:8000
      SERVICE_NAME: order-service
      LOG_LEVEL: INFO
    depends_on:
      postgres-orders:
        condition: service_healthy
      rabbitmq:
        condition: service_healthy
      product-service:
        condition: service_started
    networks:
      - backend-network
      - database-network
    restart: unless-stopped

  notification-service:
    build: ./notification-service
    container_name: notification-service
    ports:
      - "8003:8000"
    environment:
      RABBITMQ_URL: amqp://guest:guest@rabbitmq:5672/
      SERVICE_NAME: notification-service
      LOG_LEVEL: INFO
      EMAIL_SERVICE: console
    depends_on:
      rabbitmq:
        condition: service_healthy
    networks:
      - backend-network
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - backend-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
    depends_on:
      - prometheus
    networks:
      - backend-network
    restart: unless-stopped

networks:
  backend-network:
    driver: bridge
  database-network:
    driver: bridge

volumes:
  products-data:
  orders-data:
  rabbitmq-data:
  prometheus-data:
  grafana-data:
```

---

## 7. ТИПИ ВЗАЄМОДІЇ В СИСТЕМІ

### 7.1. Синхронна взаємодія (REST API)

#### Order Service → Product Service

**Use Case:** Перевірка товару перед створенням замовлення

**Протокол:** HTTP/JSON

**Endpoint:** `GET http://product-service:8000/products/{id}`

**Характеристики:**
- **Тип:** Request/Response
- **Timeout:** 5 секунд
- **Retry strategy:** 3 спроби з експоненціальною затримкою (1s, 2s, 4s)
- **Circuit breaker:** Відкривається після 5 невдалих запитів, відновлюється через 60 секунд

**Приклад запиту:**
```http
GET http://product-service:8000/products/1 HTTP/1.1
Host: product-service:8000
Accept: application/json
X-Request-ID: uuid-v4
X-Correlation-ID: trace-id
```

**Приклад відповіді (успіх):**
```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "id": 1,
  "name": "Ноутбук Lenovo ThinkPad",
  "description": "Професійний ноутбук",
  "price": 25999.99,
  "stock": 15,
  "category": "Електроніка"
}
```

**Приклад відповіді (помилка):**
```http
HTTP/1.1 404 Not Found
Content-Type: application/json

{
  "error": "NotFound",
  "message": "Product with id=1 not found",
  "timestamp": "2025-11-15T10:35:00Z"
}
```

**Переваги для цього use case:**
- ✅ Негайне отримання актуальних даних про товар
- ✅ Можливість валідувати наявність перед створенням замовлення
- ✅ Простота реалізації та дебагу

**Недоліки:**
- ❌ Жорстка залежність (якщо Product Service недоступний, замовлення не створюється)
- ❌ Додаткова затримка у відповіді клієнту (~50-100 мс)

**Альтернативи:**
1. **Кешування:** Зберігати копію даних про товари в Order Service (eventual consistency)
2. **Read Replica:** Читати з реплік Product Service для розподілення навантаження
3. **API Gateway:** Централізована точка для агрегації даних

---

### 7.2. Асинхронна взаємодія (RabbitMQ)

#### Order Service → Product Service + Notification Service

**Use Case:** Сповіщення про створене замовлення та оновлення залишків

**Протокол:** AMQP (Advanced Message Queuing Protocol)

**Архітектура:**
```
Order Service (Publisher)
    ↓
    Publish to Exchange: "orders_exchange" (type: topic)
    ↓
RabbitMQ Broker
    ├─ Queue: "order.created" → Product Service (Consumer)
    └─ Queue: "order.created" → Notification Service (Consumer)
```

**Конфігурація RabbitMQ:**

**Exchange:**
- Name: `orders_exchange`
- Type: `topic`
- Durable: `true`
- Auto-delete: `false`

**Queue #1 (Product Service):**
- Name: `order.created.product`
- Routing Key: `order.created`
- Durable: `true`
- Exclusive: `false`
- Auto-ack: `false` (manual acknowledgement)
- Prefetch count: 10

**Queue #2 (Notification Service):**
- Name: `order.created.notification`
- Routing Key: `order.created`
- Durable: `true`
- Exclusive: `false`
- Auto-ack: `false`
- Prefetch count: 5

**Формат події OrderCreated:**
```json
{
  "event_type": "OrderCreated",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_version": "1.0",
  "timestamp": "2025-11-15T10:35:00.123Z",
  "source": "order-service",
  "correlation_id": "trace-12345",
  "data": {
    "order_id": 101,
    "product_id": 1,
    "product_name": "Ноутбук Lenovo ThinkPad",
    "quantity": 2,
    "unit_price": 25999.99,
    "total_price": 51999.98,
    "customer_email": "customer@example.com",
    "status": "pending"
  },
  "metadata": {
    "retry_count": 0,
    "priority": "normal"
  }
}
```

**Публікація події (Order Service):**
```python
import pika
import json
from datetime import datetime
import uuid

def publish_order_created(order_data):
    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )
    channel = connection.channel()
    
    # Declare exchange
    channel.exchange_declare(
        exchange='orders_exchange',
        exchange_type='topic',
        durable=True
    )
    
    # Create event
    event = {
        "event_type": "OrderCreated",
        "event_id": str(uuid.uuid4()),
        "event_version": "1.0",
        "timestamp": datetime.utcnow().isoformat(),
        "source": "order-service",
        "data": order_data
    }
    
    # Publish
    channel.basic_publish(
        exchange='orders_exchange',
        routing_key='order.created',
        body=json.dumps(event),
        properties=pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type='application/json',
            correlation_id=str(uuid.uuid4())
        )
    )
    
    connection.close()
```

**Споживання події (Product Service):**
```python
import pika
import json

def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
        order_data = event['data']
        
        # Update stock
        product_id = order_data['product_id']
        quantity = order_data['quantity']
        
        update_stock(product_id, -quantity)
        
        # Acknowledge message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        print(f"✓ Stock updated for product {product_id}")
        
    except Exception as e:
        print(f"✗ Error processing event: {e}")
        # Reject and requeue (or send to DLQ)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

def start_consumer():
    connection = pika.BlockingConnection(
        pika.URLParameters(RABBITMQ_URL)
    )
    channel = connection.channel()
    
    # Declare queue
    channel.queue_declare(
        queue='order.created.product',
        durable=True
    )
    
    # Bind queue to exchange
    channel.queue_bind(
        exchange='orders_exchange',
        queue='order.created.product',
        routing_key='order.created'
    )
    
    # Set prefetch count
    channel.basic_qos(prefetch_count=10)
    
    # Start consuming
    channel.basic_consume(
        queue='order.created.product',
        on_message_callback=callback,
        auto_ack=False
    )
    
    print("Waiting for messages...")
    channel.start_consuming()
```

**Переваги асинхронної взаємодії:**
- ✅ Слабка зв'язаність (loose coupling)
- ✅ Відмовостійкість (повідомлення не втрачаються)
- ✅ Масштабованість (можна додати багато споживачів)
- ✅ Незалежність обробки (не блокує основний потік)

**Недоліки:**
- ❌ Eventual consistency (затримка оновлення даних)
- ❌ Складність налагодження
- ❌ Потрібен додатковий компонент (RabbitMQ)

---

### 7.3. Порівняння типів взаємодії

| Характеристика | Синхронна (REST) | Асинхронна (RabbitMQ) |
|----------------|------------------|------------------------|
| **Тип зв'язку** | Tight coupling | Loose coupling |
| **Затримка** | 50-100 мс | 100-500 мс |
| **Відмовостійкість** | Низька (залежить від доступності) | Висока (черга зберігає повідомлення) |
| **Масштабування** | Складніше | Легше (додати споживачів) |
| **Узгодженість даних** | Strong consistency | Eventual consistency |
| **Складність** | Проста | Середня |
| **Use Cases** | Критичні операції, що потребують негайної відповіді | Фонові задачі, сповіщення, оновлення даних |
| **Приклади у системі** | Order → Product (перевірка товару) | Order → Product (оновлення stock), Order → Notification (email) |

---

## 8. ОБРОБКА ПОМИЛОК ТА RETRY ЛОГІКА

### 8.1. Стратегія обробки помилок у синхронній взаємодії

#### Exponential Backoff Retry

**Алгоритм:**
```python
import time
import httpx

async def call_product_service_with_retry(product_id: int, max_retries: int = 3):
    base_delay = 1  # секунда
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{PRODUCT_SERVICE_URL}/products/{product_id}"
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise ProductNotFoundError(f"Product {product_id} not found")
                else:
                    raise ProductServiceError(f"Unexpected status: {response.status_code}")
                    
        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # 1s, 2s, 4s
                print(f"Timeout. Retry {attempt + 1}/{max_retries} after {delay}s")
                await asyncio.sleep(delay)
            else:
                raise ProductServiceUnavailableError("Product Service unavailable after 3 retries")
        
        except httpx.ConnectError:
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                print(f"Connection error. Retry {attempt + 1}/{max_retries} after {delay}s")
                await asyncio.sleep(delay)
            else:
                raise ProductServiceUnavailableError("Cannot connect to Product Service")
```

**Діаграма Exponential Backoff:**
```
Спроба 1: 0 секунд       → Помилка
           ↓ Wait 1s
Спроба 2: 1 секунда      → Помилка
           ↓ Wait 2s
Спроба 3: 3 секунди      → Помилка
           ↓ Wait 4s
Спроба 4: 7 секунд       → Відмова (503 Service Unavailable)
```

#### Circuit Breaker Pattern

**Стани Circuit Breaker:**

1. **CLOSED (Закритий)** - нормальна робота
   - Запити проходять до сервісу
   - Лічильник помилок = 0

2. **OPEN (Відкритий)** - сервіс недоступний
   - Запити негайно відхиляються (fail fast)
   - Не навантажує недоступний сервіс
   - Після timeout переходить у HALF-OPEN

3. **HALF-OPEN (Напіввідкритий)** - тестування відновлення
   - Пропускає обмежену кількість запитів
   - Якщо успішно → CLOSED
   - Якщо помилка → OPEN

**Реалізація:**
```python
from circuitbreaker import circuit

@circuit(failure_threshold=5, recovery_timeout=60, expected_exception=ProductServiceError)
async def get_product(product_id: int):
    """
    failure_threshold: відкриється після 5 помилок
    recovery_timeout: перейде в HALF-OPEN через 60 секунд
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        response = await client.get(f"{PRODUCT_SERVICE_URL}/products/{product_id}")
        
        if response.status_code != 200:
            raise ProductServiceError(f"Status: {response.status_code}")
        
        return response.json()
```

**Діаграма станів:**
```
CLOSED ──(5 failures)──> OPEN ──(60s timeout)──> HALF-OPEN
   ↑                                                   |
   └─────────────────(1 success)────────────────────┘
   
HALF-OPEN ──(failure)──> OPEN
```

---

### 8.2. Стратегія обробки помилок у асинхронній взаємодії

#### Dead Letter Queue (DLQ)

**Конфігурація:**
```python
# Створення основної черги з DLQ
channel.queue_declare(
    queue='order.created.product',
    durable=True,
    arguments={
        'x-dead-letter-exchange': 'dlx_exchange',
        'x-dead-letter-routing-key': 'order.created.dlq',
        'x-message-ttl': 60000,  # 60 секунд
        'x-max-retries': 3
    }
)

# Створення Dead Letter Queue
channel.queue_declare(
    queue='order.created.product.dlq',
    durable=True
)
```

**Обробка з retry логікою:**
```python
def callback(ch, method, properties, body):
    try:
        event = json.loads(body)
        retry_count = event.get('metadata', {}).get('retry_count', 0)
        
        # Process event
        process_order_created(event)
        
        # Success - acknowledge
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except TemporaryError as e:
        # Recoverable error - retry
        if retry_count < 3:
            event['metadata']['retry_count'] = retry_count + 1
            
            # Requeue with delay
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
            print(f"Retry {retry_count + 1}/3 for event {event['event_id']}")
        else:
            # Max retries reached - send to DLQ
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            print(f"Max retries reached. Sent to DLQ: {event['event_id']}")
    
    except PermanentError as e:
        # Unrecoverable error - send to DLQ immediately
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        print(f"Permanent error. Sent to DLQ: {event['event_id']}")
```

**Архітектура з DLQ:**
```
orders_exchange
    ↓
order.created.product (main queue)
    ├─ Success → ACK → Message removed
    ├─ Retry (< 3) → NACK (requeue=True) → Back to queue
    └─ Failed (>= 3) → NACK (requeue=False) → DLQ
                                                  ↓
                                    order.created.product.dlq
                                                  ↓
                                    Manual inspection / reprocessing
```

#### Idempotency (Ідемпотентність)

**Проблема:** Повідомлення може бути доставлено більше одного разу

**Рішення:** Перевірка унікальності події перед обробкою

```python
# Таблиця для відстеження оброблених подій
CREATE TABLE processed_events (
    event_id UUID PRIMARY KEY,
    event_type VARCHAR(100),
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

def process_order_created(event):
    event_id = event['event_id']
    
    # Check if already processed
    if is_event_processed(event_id):
        print(f"Event {event_id} already processed. Skipping.")
        return
    
    # Process event
    order_data = event['data']
    update_stock(order_data['product_id'], -order_data['quantity'])
    
    # Mark as processed
    mark_event_processed(event_id, event['event_type'])
    print(f"Event {event_id} processed successfully")
```

---

## 9. ВИСНОВКИ

У ході виконання лабораторної роботи №3 було успішно змодельовано взаємодію між мікросервісами системи управління замовленнями онлайн-магазину.

**Основні результати:**

1. **Обрано та детально описано use case "Створення замовлення":**
   - Визначено всіх учасників взаємодії (7 компонентів)
   - Описано основний потік (13 кроків)
   - Визначено 4 альтернативні потоки (помилкові сценарії)

2. **Створено 3 Sequence Diagrams:**
   - Успішний потік створення замовлення (24 кроки)
   - Недостатньо товару на складі (альтернативний потік)
   - Product Service недоступний з retry механізмом

3. **Створено Deployment Diagram:**
   - 8 Docker контейнерів
   - 3 мережеві сегменти
   - Детальна конфігурація інфраструктури
   - Health checks та restart policies

4. **Визначено типи взаємодії:**
   - **Синхронна (REST):** Order Service → Product Service
     - Timeout: 5 секунд
     - Retry: 3 спроби з exponential backoff
     - Circuit breaker після 5 помилок
   - **Асинхронна (RabbitMQ):** Order Service → Product/Notification Services
     - Durable queues
     - Manual acknowledgement
     - Dead Letter Queue для помилок

5. **Описано стратегії обробки помилок:**
   - Exponential backoff для синхронних викликів
   - Circuit breaker pattern для fault tolerance
   - Dead Letter Queue для асинхронних повідомлень
   - Idempotency для запобігання дублюванню обробки

6. **Проаналізовано критичні моменти:**
   - Single Point of Failure: Product Service у синхронному виклику
   - Eventual consistency: затримка 100-500 мс у оновленні залишків
   - Trade-offs: strong consistency vs availability

**Ключові метрики системи:**
- Час створення замовлення (E2E): 300-500 мс
- Час синхронного виклику Product Service: 50-100 мс
- Час публікації події в RabbitMQ: 10-20 мс
- Час обробки події Product Service: 100-200 мс
- Час обробки події Notification Service: 300-500 мс

**Переваги спроєктованої взаємодії:**
- ✅ Балансує між strong і eventual consistency
- ✅ Забезпечує відмовостійкість через асинхронність
- ✅ Дозволяє масштабувати компоненти незалежно
- ✅ Зменшує навантаження на критичні сервіси

**Можливості для покращення:**
1. Додати кешування даних про товари в Order Service
2. Використати API Gateway для централізованої маршрутизації
3. Впровадити distributed tracing (Jaeger/Zipkin)
4. Додати rate limiting для захисту від перевантаження

Спроєктована взаємодія повністю відповідає архітектурі, визначеній у Лабораторних роботах №1 та №2, та забезпечує надійну, масштабовану комунікацію між мікросервісами.

---

## 10. ВІДПОВІДІ НА КОНТРОЛЬНІ ЗАПИТАННЯ

**1. Які є види міжсервісної взаємодії?**

Існує два основні види міжсервісної взаємодії:

**Синхронна взаємодія:**
- Клієнт надсилає запит і чекає на відповідь
- Блокуюча операція
- Протоколи: REST (HTTP/HTTPS), gRPC
- **Приклад у нашій системі:** Order Service викликає Product Service для перевірки товару

**Асинхронна взаємодія:**
- Відправник надсилає повідомлення і продовжує роботу
- Неблокуюча операція
- Протоколи: AMQP (RabbitMQ), Kafka, NATS
- **Приклад у нашій системі:** Order Service публікує подію OrderCreated, яку обробляють Product Service та Notification Service

**Гібридна взаємодія:**
- Комбінація синхронної та асинхронної
- **Наша система використовує гібридний підхід:** синхронно перевіряє товар, асинхронно оновлює залишки

**2. У чому різниця між синхронною та асинхронною взаємодією?**

| Характеристика | Синхронна | Асинхронна |
|----------------|-----------|------------|
| **Очікування відповіді** | Так (блокування) | Ні (неблокування) |
| **Зв'язаність** | Tight coupling | Loose coupling |
| **Consistency** | Strong consistency | Eventual consistency |
| **Відмовостійкість** | Низька (каскадні збої) | Висока (черга зберігає повідомлення) |
| **Затримка** | Низька (50-100 мс) | Вища (100-500 мс) |
| **Складність** | Проста | Середня |
| **Масштабування** | Складніше | Легше |

**Коли використовувати синхронну:**
- Потрібна негайна відповідь
- Критична операція (наприклад, перевірка наявності товару)
- Простий запит-відповідь

**Коли використовувати асинхронну:**
- Фонові задачі (оновлення залишків, сповіщення)
- Довготривалі операції
- Потрібна висока відмовостійкість
- Масштабування споживачів

**3. Що таке брокер повідомлень?**

**Брокер повідомлень (Message Broker)** - це посередник між сервісами, який приймає, зберігає та доставляє повідомлення від відправників (publishers) до отримувачів (consumers).

**Основні функції:**
1. **Прийом повідомлень** від publishers
2. **Зберігання** повідомлень у чергах (queues)
3. **Маршрутизація** повідомлень через exchanges (RabbitMQ)
4. **Доставка** повідомлень до consumers
5. **Гарантування** доставки (persistent messages)

**У нашій системі (RabbitMQ):**
- **Publisher:** Order Service
- **Broker:** RabbitMQ з exchange `orders_exchange`
- **Consumers:** Product Service, Notification Service
- **Queue:** `order.created.product`, `order.created.notification`

**Переваги використання брокера:**
- ✅ Decoupling: сервіси не знають один про одного
- ✅ Reliability: повідомлення не втрачаються при збоях
- ✅ Scalability: легко додавати нових споживачів
- ✅ Load leveling: згладжування пікових навантажень

**Популярні брокери:**
- RabbitMQ - універсальний, підтримує різні протоколи
- Apache Kafka - для потокової обробки великих обсягів даних
- NATS - легковаговий, для мікросервісів
- Redis Streams - вбудований у Redis

**4. Які переваги має подійно-орієнтована архітектура?**

**Подійно-орієнтована архітектура (Event-Driven Architecture, EDA)** - це підхід, де система реагує на події, а не на прямі виклики.

**Переваги:**

1. **Loose Coupling (Слабка зв'язаність):**
   - Сервіси не знають один про одного
   - Можна додавати нових споживачів без зміни publisher'а
   - **Приклад:** Order Service не знає про існування Notification Service

2. **Scalability (Масштабованість):**
   - Можна додавати необмежену кількість споживачів
   - Кожен сервіс масштабується незалежно
   - **Приклад:** Можна запустити 5 екземплярів Notification Service для обробки багатьох сповіщень

3. **Resilience (Відмовостійкість):**
   - Якщо споживач недоступний, події залишаються в черзі
   - Система продовжує працювати при збоях окремих компонентів
   - **Приклад:** Якщо Notification Service падає, Order Service все одно створює замовлення

4. **Asynchronous Processing (Асинхронна обробка):**
   - Не блокує основний потік
   - Швидша відповідь клієнту
   - **Приклад:** Order Service одразу повертає відповідь покупцю, не чекаючи на оновлення залишків

5. **Audit Trail (Історія подій):**
   - Всі події зберігаються
   - Можна відтворити послідовність подій
   - **Приклад:** Можна побачити всі OrderCreated події за день

6. **Real-time Processing (Обробка в реальному часі):**
   - Події обробляються негайно після публікації
   - **Приклад:** Сповіщення надсилається через 100-500 мс після створення замовлення

**Недоліки:**
- ❌ Складність налагодження (distributed tracing необхідний)
- ❌ Eventual consistency (дані не завжди узгоджені миттєво)
- ❌ Потрібен надійний брокер повідомлень

**5. Для чого використовують діаграму послідовності?**

**Sequence Diagram (Діаграма послідовності)** - це UML діаграма, яка показує, як об'єкти взаємодіють між собою у часі, відображаючи послідовність повідомлень.

**Призначення:**

1. **Візуалізація потоків даних:**
   - Показує порядок викликів між компонентами
   - Демонструє, хто кого викликає і в якому порядку
   - **Приклад:** Наша діаграма показує 24 кроки створення замовлення

2. **Документування взаємодії:**
   - Служить технічною документацією
   - Допомагає новим розробникам зрозуміти систему
   - Зберігає знання про архітектуру

3. **Виявлення проблем:**
   - Показує вузькі місця (bottlenecks)
   - Виявляє зайві виклики або складну логіку
   - **Приклад:** Бачимо, що синхронний виклик Product Service - potential single point of failure

4. **Аналіз часу виконання:**
   - Можна оцінити затримки на кожному кроці
   - Визначити, які операції займають найбільше часу
   - **Приклад:** Синхронний виклик 50-100 мс, асинхронна обробка 100-500 мс

5. **Проєктування нових фіч:**
   - Допомагає спланувати взаємодію до написання коду
   - Дозволяє обговорити з командою
   - Виявити проблеми на етапі проєктування

6. **Тестування та дебаг:**
   - Розуміння, які кроки потрібно перевірити
   - Допомагає відтворити проблему
   - **Приклад:** Якщо замовлення не створюється, дивимось на кроки 1-13

**Елементи Sequence Diagram:**
- **Actors** - зовнішні користувачі
- **Participants** - сервіси, бази даних
- **Arrows** - повідомлення між учасниками
- **Activation boxes** - час активності об'єкта
- **Notes** - додаткові пояснення

**6. Що означає ідемпотентність сервісу?**

**Ідемпотентність (Idempotency)** - це властивість операції, яка дає однаковий результат при виконанні один або кілька разів з однаков