"""
Order Repository - Data Access Layer
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.order import Order
from app.schemas.order import OrderCreate


class OrderRepository:
    """Repository for Order CRUD operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Order]:
        """Get all orders with pagination"""
        return self.db.query(Order).order_by(
            desc(Order.created_at)
        ).offset(skip).limit(limit).all()
    
    def get_by_id(self, order_id: int) -> Optional[Order]:
        """Get order by ID"""
        return self.db.query(Order).filter(Order.id == order_id).first()
    
    def get_by_status(self, status: str) -> List[Order]:
        """Get orders by status"""
        return self.db.query(Order).filter(
            Order.status == status
        ).order_by(desc(Order.created_at)).all()
    
    def get_by_customer_email(self, email: str) -> List[Order]:
        """Get orders by customer email"""
        return self.db.query(Order).filter(
            Order.customer_email == email
        ).order_by(desc(Order.created_at)).all()
    
    def create(self, order_data: dict) -> Order:
        """
        Create new order
        
        Args:
            order_data: Dictionary with order fields
        
        Returns:
            Created order
        """
        order = Order(**order_data)
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def update_status(self, order_id: int, new_status: str) -> Optional[Order]:
        """Update order status"""
        order = self.get_by_id(order_id)
        if not order:
            return None
        
        order.status = new_status
        self.db.commit()
        self.db.refresh(order)
        return order
    
    def count(self) -> int:
        """Get total count of orders"""
        return self.db.query(Order).count()
    
    def count_by_status(self, status: str) -> int:
        """Get count of orders by status"""
        return self.db.query(Order).filter(Order.status == status).count()