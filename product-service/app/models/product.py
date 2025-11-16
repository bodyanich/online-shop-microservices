"""
SQLAlchemy Product model
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, CheckConstraint
from sqlalchemy.sql import func
from app.database import Base


class Product(Base):
    """Product database model"""
    
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    stock = Column(Integer, nullable=False, default=0)
    category = Column(String(100), nullable=True, index=True)
    image_url = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Constraints
    __table_args__ = (
        CheckConstraint('price >= 0', name='check_price_positive'),
        CheckConstraint('stock >= 0', name='check_stock_non_negative'),
    )
    
    def __repr__(self):
        return f"<Product(id={self.id}, name='{self.name}', price={self.price}, stock={self.stock})>"


class ProcessedEvent(Base):
    """Table to track processed RabbitMQ events for idempotency"""
    
    __tablename__ = "processed_events"
    
    event_id = Column(String(100), primary_key=True, unique=True, nullable=False)
    event_type = Column(String(100), nullable=False)
    processed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    def __repr__(self):
        return f"<ProcessedEvent(event_id='{self.event_id}', event_type='{self.event_type}')>"