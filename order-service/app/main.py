"""
FastAPI Application Entry Point - Order Service
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.config import settings
from app.database import init_db
from app.api import orders, health

# Create FastAPI application
app = FastAPI(
    title="Order Service",
    description="Microservice for managing orders and order processing",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router)
app.include_router(orders.router)

# Prometheus metrics
Instrumentator().instrument(app).expose(app)


@app.on_event("startup")
def startup_event():
    """Initialize database on startup"""
    print(f"Starting {settings.SERVICE_NAME}...")
    init_db()
    print(f"✓ Database initialized")
    print(f"✓ Product Service URL: {settings.PRODUCT_SERVICE_URL}")
    print(f"✓ RabbitMQ URL: {settings.RABBITMQ_URL}")
    print(f"✓ {settings.SERVICE_NAME} is running on port {settings.SERVICE_PORT}")


@app.on_event("shutdown")
def shutdown_event():
    """Cleanup on shutdown"""
    print(f"Shutting down {settings.SERVICE_NAME}...")