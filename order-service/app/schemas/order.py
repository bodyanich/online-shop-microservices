"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import Optional, Literal
from datetime import datetime


class OrderBase(BaseModel):
    """Base Order schema"""
    product_id: int = Field(..., gt=0, description="Product ID")
    quantity: int = Field(..., gt=0, description="Quantity to order")
    customer_email: Optional[EmailStr] = Field(None, description="Customer email address")


class OrderCreate(OrderBase):
    """Schema for creating a new order"""
    pass


class OrderStatusUpdate(BaseModel):
    """Schema for updating order status"""
    status: Literal['pending', 'processing', 'completed', 'cancelled'] = Field(
        ..., 
        description="Order status"
    )


class OrderResponse(BaseModel):
    """Schema for order response"""
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    status: str
    customer_email: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class OrderListResponse(BaseModel):
    """Schema for list of orders response"""
    orders: list[OrderResponse]
    total: int


class OrderCreatedEvent(BaseModel):
    """Schema for OrderCreated event payload"""
    event_type: str = "OrderCreated"
    event_id: str
    event_version: str = "1.0"
    timestamp: str
    source: str = "order-service"
    data: dict