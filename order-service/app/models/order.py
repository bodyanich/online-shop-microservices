"""
SQLAlchemy Order model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class Order(Base):
    """Order database model"""
    
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    product_id = Column(Integer, nullable=False, index=True)
    product_name = Column(String(255), nullable=False)  # Denormalized for history
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    status = Column(String(50), nullable=False, default='pending', index=True)
    customer_email = Column(String(255), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_quantity_positive'),
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'cancelled')", name='check_status_valid'),
    )
    
    def __repr__(self):
        return f"<Order(id={self.id}, product_id={self.product_id}, quantity={self.quantity}, status='{self.status}')>"