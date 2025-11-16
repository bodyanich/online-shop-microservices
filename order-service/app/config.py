"""
Configuration settings for Order Service
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost:5433/orders_db"
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_EXCHANGE: str = "orders_exchange"
    RABBITMQ_ROUTING_KEY: str = "order.created"
    
    # Product Service
    PRODUCT_SERVICE_URL: str = "http://localhost:8001"
    
    # Service
    SERVICE_NAME: str = "order-service"
    SERVICE_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:8080"
    ]
    
    # Retry Configuration
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()