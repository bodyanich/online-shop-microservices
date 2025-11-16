"""
Health check endpoint
"""
from fastapi import APIRouter
from datetime import datetime

from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """
    Health check endpoint
    
    Returns service health status
    """
    return {
        "service": settings.SERVICE_NAME,
        "status": "healthy",
        "email_service": settings.EMAIL_SERVICE,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/")
def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "description": "Notification service for sending order notifications"
    }