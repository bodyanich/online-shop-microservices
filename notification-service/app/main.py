"""
FastAPI Application Entry Point - Notification Service
"""
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.api import health

# Create FastAPI application (minimal - mainly for health checks)
app = FastAPI(
    title="Notification Service",
    description="Microservice for sending order notifications",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Include routers
app.include_router(health.router)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def startup_event():
    """Startup event"""
    print(f"Starting {settings.SERVICE_NAME}...")
    print(f"✓ Email service: {settings.EMAIL_SERVICE}")
    print(f"✓ RabbitMQ URL: {settings.RABBITMQ_URL}")
    print(f"✓ {settings.SERVICE_NAME} API is running on port {settings.SERVICE_PORT}")
    print(f"✓ To start consumer, run: python run_consumer.py")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    print(f"Shutting down {settings.SERVICE_NAME}...")