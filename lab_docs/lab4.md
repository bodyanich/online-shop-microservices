# ЛАБОРАТОРНА РОБОТА №4
## Технологічна архітектура

**Тема проекту:** Система управління замовленнями у невеликому онлайн-магазині

**Виконав:** [Ваше ім'я]  
**Група:** [Ваша група]  
**Дата:** 15.11.2025

---

## 1. МЕТА РОБОТИ

Розробити схему технологічного забезпечення розподіленої програмної системи, обрати стек технологій, описати топологію розгортання у хмарі та визначити способи забезпечення стійкості системи.

---

## 2. ТЕХНОЛОГІЧНИЙ СТЕК

### 2.1. Backend Framework
**FastAPI 0.104+** (Python 3.11+)
- Async/await підтримка
- Автоматична OpenAPI документація
- High performance (порівняно з Flask/Django)
- Type hints validation через Pydantic

### 2.2. База даних
**PostgreSQL 15**
- ACID транзакції
- JSON підтримка
- Replication можливості
- Mature ecosystem

### 2.3. Message Broker
**RabbitMQ 3**
- AMQP протокол
- Guaranteed delivery
- Durable queues
- Management UI

### 2.4. Контейнеризація
**Docker 24+**
- Ізоляція середовищ
- Reproducible builds
- Multi-stage builds

**Docker Compose 2.0**
- Локальна розробка
- Multi-container orchestration

### 2.5. Оркестрація
**Azure Kubernetes Service (AKS)**
- Managed Kubernetes
- Auto-scaling
- High availability
- Azure integration

### 2.6. Моніторинг
**Prometheus + Grafana**
- Metrics collection
- Time-series database
- Visualization dashboards
- Alerting

### 2.7. Додаткові бібліотеки

| Бібліотека | Версія | Призначення |
|------------|--------|-------------|
| SQLAlchemy | 2.0+ | ORM |
| Pydantic | 2.0+ | Data validation |
| Alembic | 1.12+ | DB migrations |
| Pika | 1.3+ | RabbitMQ client |
| httpx | 0.25+ | Async HTTP client |
| prometheus-fastapi-instrumentator | 6.1+ | Metrics export |

---

## 3. ТОПОЛОГІЯ РОЗГОРТАННЯ У ХМАРІ AZURE

### 3.1. Azure Resources

**Resource Group:** `rg-online-shop-prod`  
**Region:** West Europe

#### Compute

**Azure Kubernetes Service (AKS)**
- Cluster: `aks-online-shop`
- Node count: 3 (Standard_D2s_v3)
- vCPU: 2 per node
- RAM: 8 GB per node
- OS: Ubuntu 22.04

#### Database

**Azure Database for PostgreSQL - Flexible Server**
- **products-db:** `psql-products-prod`
  - SKU: Standard_B2s (2 vCores, 4 GB RAM)
  - Storage: 32 GB
  - Backup retention: 7 days
  
- **orders-db:** `psql-orders-prod`
  - SKU: Standard_B2s (2 vCores, 4 GB RAM)
  - Storage: 32 GB
  - Backup retention: 7 days

#### Messaging

**Azure Service Bus** (альтернатива RabbitMQ у хмарі)
- Namespace: `sb-online-shop`
- Tier: Standard
- Queue: `order-created`

**Або VM з RabbitMQ:**
- VM: `vm-rabbitmq` (Standard_B2s)
- Managed disk: 32 GB SSD

#### Networking

**Virtual Network (VNet):** `vnet-online-shop`
- Address space: 10.0.0.0/16

**Subnets:**
- `subnet-aks`: 10.0.1.0/24 (AKS nodes)
- `subnet-db`: 10.0.2.0/24 (PostgreSQL)
- `subnet-services`: 10.0.3.0/24 (RabbitMQ VM)

**Azure Load Balancer**
- Type: Standard
- Public IP: Static
- Backend pool: AKS nodes

#### Storage

**Azure Container Registry (ACR)**
- Name: `acronlineshop`
- SKU: Basic
- Docker images: product-service, order-service, notification-service

#### Monitoring

**Azure Monitor + Log Analytics**
- Workspace: `log-online-shop`
- Application Insights: Enabled

**Prometheus + Grafana (on AKS)**
- Deployed as Kubernetes services

### 3.2. Deployment Diagram (Azure)

```plantuml
@startuml Azure_Deployment

!define AzurePuml https://raw.githubusercontent.com/plantuml-stdlib/Azure-PlantUML/release/2-2/dist
!includeurl AzurePuml/AzureCommon.puml
!includeurl AzurePuml/Compute/AzureKubernetesService.puml
!includeurl AzurePuml/Databases/AzureDatabaseForPostgreSQL.puml
!includeurl AzurePuml/Networking/AzureLoadBalancer.puml
!includeurl AzurePuml/Containers/AzureContainerRegistry.puml

title Топологія розгортання у Microsoft Azure

package "Azure Cloud - West Europe" {
    
    package "Resource Group: rg-online-shop-prod" {
        
        AzureLoadBalancer(lb, "Azure Load Balancer", "Standard")
        
        AzureKubernetesService(aks, "AKS Cluster", "aks-online-shop\n3 nodes (Standard_D2s_v3)")
        
        package "AKS Workloads" {
            rectangle "Product Service\n(3 replicas)" as ps
            rectangle "Order Service\n(3 replicas)" as os
            rectangle "Notification Service\n(2 replicas)" as ns
            rectangle "RabbitMQ\n(1 replica)" as rmq
            rectangle "Prometheus" as prom
            rectangle "Grafana" as grafana
        }
        
        AzureDatabaseForPostgreSQL(db1, "products-db", "Standard_B2s\n4GB RAM")
        AzureDatabaseForPostgreSQL(db2, "orders-db", "Standard_B2s\n4GB RAM")
        
        AzureContainerRegistry(acr, "ACR", "acronlineshop")
    }
}

actor "Customer" as customer
actor "Admin" as admin

customer --> lb : HTTPS
admin --> lb : HTTPS
lb --> aks : Routes traffic
aks --> ps
aks --> os
aks --> ns
aks --> rmq

ps --> db1 : SQL/TCP
os --> db2 : SQL/TCP
os --> rmq : AMQP
rmq --> ps : AMQP
rmq --> ns : AMQP

acr --> aks : Pull images

@enduml
```

### 3.3. Kubernetes Resources

#### Deployments

**product-service**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: product-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: product-service
  template:
    metadata:
      labels:
        app: product-service
    spec:
      containers:
      - name: product-service
        image: acronlineshop.azurecr.io/product-service:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

**order-service**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: order-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: order-service
  template:
    metadata:
      labels:
        app: order-service
    spec:
      containers:
      - name: order-service
        image: acronlineshop.azurecr.io/order-service:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 250m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
```

**notification-service**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: notification-service
spec:
  replicas: 2
  selector:
    matchLabels:
      app: notification-service
  template:
    metadata:
      labels:
        app: notification-service
    spec:
      containers:
      - name: notification-service
        image: acronlineshop.azurecr.io/notification-service:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 250m
            memory: 256Mi
```

#### Services

**product-service-svc**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: product-service
spec:
  type: ClusterIP
  selector:
    app: product-service
  ports:
  - port: 8000
    targetPort: 8000
```

**order-service-svc**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: order-service
spec:
  type: LoadBalancer
  selector:
    app: order-service
  ports:
  - port: 80
    targetPort: 8000
```

---

## 4. СПОСОБИ ЗАБЕЗПЕЧЕННЯ СТІЙКОСТІ

### 4.1. Load Balancer

#### Azure Load Balancer (L4)
- **Type:** Standard Load Balancer
- **Frontend IP:** Public Static IP
- **Backend Pool:** AKS worker nodes
- **Health Probe:** HTTP /health endpoint
- **Load Distribution:** Round-robin
- **Session Persistence:** None (stateless services)

#### Kubernetes Service (L7)
- **Type:** LoadBalancer / ClusterIP
- **Internal routing:** kube-proxy (iptables)
- **Algorithm:** Round-robin between pods

**Traffic Flow:**
```
Internet → Azure LB (Public IP) → AKS Ingress Controller → K8s Service → Pods
```

### 4.2. Replica Sets

#### Product Service
- **Replicas:** 3
- **Strategy:** RollingUpdate
- **Max Surge:** 1
- **Max Unavailable:** 1

#### Order Service
- **Replicas:** 3
- **Strategy:** RollingUpdate
- **Max Surge:** 1
- **Max Unavailable:** 1

#### Notification Service
- **Replicas:** 2
- **Strategy:** RollingUpdate
- **Max Surge:** 1
- **Max Unavailable:** 0

#### PostgreSQL
- **Primary:** 1 instance
- **Standby (HA):** 1 read replica
- **Failover:** Automatic (Azure managed)

#### RabbitMQ
- **Replicas:** 1 (можна 3 для HA cluster)
- **Persistent Volume:** Azure Disk 32GB

### 4.3. Autoscaling

#### Horizontal Pod Autoscaler (HPA)

**product-service HPA**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: product-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: product-service
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**order-service HPA**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: order-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: order-service
  minReplicas: 3
  maxReplicas: 15
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

**notification-service HPA**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: notification-service-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: notification-service
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60
```

#### Cluster Autoscaler (AKS)
```yaml
# Enable via Azure CLI
az aks update \
  --resource-group rg-online-shop-prod \
  --name aks-online-shop \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 10
```

**Trigger:** Node CPU/Memory utilization > 80%  
**Scale Up:** Add new node (takes ~3-5 minutes)  
**Scale Down:** Remove idle nodes after 10 minutes

#### Azure Database Autoscaling
- **Compute:** Manual scaling (B2s → D4s_v3)
- **Storage:** Auto-grow enabled (32GB → 128GB max)
- **IOPS:** Scaled automatically with storage

### 4.4. Health Checks

#### Kubernetes Probes

**Liveness Probe** (перевірка чи Pod живий)
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Readiness Probe** (перевірка чи Pod готовий приймати трафік)
```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 3
```

**Startup Probe** (для повільного старту)
```yaml
startupProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 0
  periodSeconds: 5
  failureThreshold: 30
```

#### Health Check Endpoint
```python
@app.get("/health")
async def health_check():
    # Check database connection
    try:
        db.execute("SELECT 1")
        db_status = "healthy"
    except:
        db_status = "unhealthy"
    
    # Check RabbitMQ connection
    try:
        rabbitmq_connection.is_open
        rabbitmq_status = "healthy"
    except:
        rabbitmq_status = "unhealthy"
    
    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "rabbitmq": rabbitmq_status,
        "timestamp": datetime.utcnow().isoformat()
    }
```

### 4.5. Resource Limits

```yaml
resources:
  requests:
    cpu: 250m        # Guaranteed CPU
    memory: 256Mi    # Guaranteed RAM
  limits:
    cpu: 500m        # Max CPU
    memory: 512Mi    # Max RAM (OOMKill if exceeded)
```

**Quality of Service Classes:**
- **Guaranteed:** requests = limits (highest priority)
- **Burstable:** requests < limits (medium priority)
- **BestEffort:** no requests/limits (lowest priority)

### 4.6. Pod Disruption Budget

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: order-service-pdb
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: order-service
```

**Гарантує:** Мінімум 2 Pods завжди доступні під час voluntary disruptions (updates, node drain)

---

## 5. ВАРТІСТЬ ІНФРАСТРУКТУРИ (Azure)

| Ресурс | SKU | Кількість | Вартість/міс (USD) |
|--------|-----|-----------|-------------------|
| AKS Cluster | Standard_D2s_v3 | 3 nodes | ~$210 |
| PostgreSQL | Standard_B2s | 2 instances | ~$100 |
| Load Balancer | Standard | 1 | ~$20 |
| Container Registry | Basic | 1 | ~$5 |
| VM RabbitMQ | Standard_B2s | 1 | ~$35 |
| Storage (Disks) | SSD 32GB | 3 | ~$15 |
| Bandwidth | Outbound | ~100GB | ~$10 |
| **TOTAL** | | | **~$395/міс** |

---

## 6. КОНТРОЛЬНІ ЗАПИТАННЯ

**1. Що таке технологічна архітектура?**

Технологічна архітектура визначає інфраструктуру, технологічний стек, способи розгортання та взаємозв'язок між апаратними і програмними ресурсами системи.

**2. Які рівні архітектури розрізняють у РПС?**

- Інфраструктурний (сервери, мережі, storage)
- Платформний (Kubernetes, бази даних, брокери)
- Рівень застосунків (мікросервіси, API)
- Рівень доступу користувачів (web, mobile, API)

**3. Які типові компоненти включає інфраструктура розподіленої системи?**

- Compute: AKS (Kubernetes), VMs
- Database: PostgreSQL Flexible Server
- Messaging: RabbitMQ / Azure Service Bus
- Networking: VNet, Load Balancer
- Storage: Container Registry, Managed Disks
- Monitoring: Prometheus, Grafana, Azure Monitor

**4. Що таке контейнер і для чого його використовують?**

Контейнер - це ізольоване середовище з застосунком та всіма залежностями. Використовується для:
- Незалежності від оточення
- Швидкого розгортання
- Масштабування
- Ізоляції ресурсів

**5. Як забезпечити масштабування у хмарному середовищі?**

- **Horizontal Pod Autoscaler:** автоматичне збільшення replicas на основі CPU/Memory
- **Cluster Autoscaler:** додавання нових nodes при необхідності
- **Load Balancer:** розподіл трафіку між replicas

**6. Яку роль відіграє балансувальник навантаження?**

- Розподіляє трафік між доступними Pods
- Виконує health checks
- Забезпечує high availability
- Підтримує session persistence (опціонально)

**7. У чому переваги Kubernetes перед Docker Compose?**

| Docker Compose | Kubernetes |
|----------------|------------|
| Одна машина | Кластер машин |
| Немає автоскейлінгу | HPA, Cluster Autoscaler |
| Ручний restart | Self-healing |
| Немає rolling updates | Zero-downtime deployments |
| Для dev/test | Для production |