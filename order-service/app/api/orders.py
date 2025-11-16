"""
Order API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.order_service import OrderService
from app.schemas.order import (
    OrderCreate,
    OrderStatusUpdate,
    OrderResponse,
    OrderListResponse
)

router = APIRouter(prefix="/orders", tags=["orders"])


def get_order_service(db: Session = Depends(get_db)) -> OrderService:
    """Dependency to get OrderService instance"""
    return OrderService(db)


@router.get("", response_model=OrderListResponse, summary="Get all orders")
def get_orders(
    skip: int = Query(0, ge=0, description="Number of orders to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of orders to return"),
    service: OrderService = Depends(get_order_service)
):
    """
    Retrieve all orders with pagination
    
    - **skip**: Number of orders to skip (default: 0)
    - **limit**: Maximum number of orders to return (default: 100, max: 1000)
    """
    return service.get_all_orders(skip=skip, limit=limit)


@router.get("/{order_id}", response_model=OrderResponse, summary="Get order by ID")
def get_order(
    order_id: int,
    service: OrderService = Depends(get_order_service)
):
    """
    Retrieve a specific order by ID
    
    - **order_id**: Order ID
    """
    order = service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id={order_id} not found"
        )
    return order


@router.post("", response_model=OrderResponse, status_code=status.HTTP_201_CREATED, summary="Create order")
async def create_order(
    order_data: OrderCreate,
    service: OrderService = Depends(get_order_service)
):
    """
    Create a new order
    
    Process:
    1. Validate product exists (call Product Service)
    2. Check stock availability
    3. Calculate total price
    4. Save order to database
    5. Publish OrderCreated event to RabbitMQ
    
    - **product_id**: Product ID (required)
    - **quantity**: Quantity to order (required, must be positive)
    - **customer_email**: Customer email (optional)
    """
    try:
        return await service.create_order(order_data)
    except ValueError as e:
        # Product not found or insufficient stock
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e)
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=str(e)
            )
    except RuntimeError as e:
        # Product Service unavailable
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )


@router.patch("/{order_id}/status", response_model=OrderResponse, summary="Update order status")
def update_order_status(
    order_id: int,
    status_data: OrderStatusUpdate,
    service: OrderService = Depends(get_order_service)
):
    """
    Update order status
    
    - **order_id**: Order ID
    - **status**: New status (pending, processing, completed, cancelled)
    """
    order = service.update_order_status(order_id, status_data.status)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Order with id={order_id} not found"
        )
    return order


@router.get("/customer/{email}", response_model=List[OrderResponse], summary="Get orders by customer")
def get_orders_by_customer(
    email: str,
    service: OrderService = Depends(get_order_service)
):
    """
    Get all orders for a specific customer
    
    - **email**: Customer email address
    """
    orders = service.get_orders_by_customer(email)
    return orders