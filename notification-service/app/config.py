"""
Configuration settings for Notification Service
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""
    
    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_QUEUE: str = "order.created.notification"
    RABBITMQ_EXCHANGE: str = "orders_exchange"
    RABBITMQ_ROUTING_KEY: str = "order.created"
    
    # Service
    SERVICE_NAME: str = "notification-service"
    SERVICE_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Email
    EMAIL_SERVICE: str = "console"  # console, sendgrid, smtp
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Create global settings instance
settings = Settings()