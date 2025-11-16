"""
Health check endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import httpx

from app.database import get_db
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint
    
    Checks:
    - Service status
    - Database connectivity
    - Product Service connectivity
    """
    # Check database
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check Product Service
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{settings.PRODUCT_SERVICE_URL}/health")
            if response.status_code == 200:
                product_service_status = "healthy"
            else:
                product_service_status = f"unhealthy: status {response.status_code}"
    except Exception as e:
        product_service_status = f"unhealthy: {str(e)}"
    
    overall_status = "healthy" if (db_status == "healthy" and product_service_status == "healthy") else "unhealthy"
    
    return {
        "service": settings.SERVICE_NAME,
        "status": overall_status,
        "database": db_status,
        "product_service": product_service_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/")
def root():
    """Root endpoint"""
    return {
        "service": settings.SERVICE_NAME,
        "version": "1.0.0",
        "docs": "/docs"
    }