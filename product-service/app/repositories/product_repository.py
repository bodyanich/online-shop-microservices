"""
Product Repository - Data Access Layer
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.models.product import Product, ProcessedEvent
from app.schemas.product import ProductCreate, ProductUpdate


class ProductRepository:
    """Repository for Product CRUD operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[Product]:
        """Get all products with pagination"""
        return self.db.query(Product).offset(skip).limit(limit).all()
    
    def get_by_id(self, product_id: int) -> Optional[Product]:
        """Get product by ID"""
        return self.db.query(Product).filter(Product.id == product_id).first()
    
    def get_by_category(self, category: str) -> List[Product]:
        """Get products by category"""
        return self.db.query(Product).filter(Product.category == category).all()
    
    def create(self, product_data: ProductCreate) -> Product:
        """Create new product"""
        product = Product(**product_data.model_dump())
        self.db.add(product)
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def update(self, product_id: int, product_data: ProductUpdate) -> Optional[Product]:
        """Update existing product"""
        product = self.get_by_id(product_id)
        if not product:
            return None
        
        # Update only provided fields
        update_data = product_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def delete(self, product_id: int) -> bool:
        """Delete product"""
        product = self.get_by_id(product_id)
        if not product:
            return False
        
        self.db.delete(product)
        self.db.commit()
        return True
    
    def update_stock(self, product_id: int, quantity_change: int) -> Optional[Product]:
        """
        Update product stock by adding/subtracting quantity
        
        Args:
            product_id: Product ID
            quantity_change: Positive to add, negative to subtract
        
        Returns:
            Updated product or None if product not found or stock becomes negative
        """
        product = self.get_by_id(product_id)
        if not product:
            return None
        
        new_stock = product.stock + quantity_change
        
        if new_stock < 0:
            raise ValueError(f"Insufficient stock. Current: {product.stock}, requested change: {quantity_change}")
        
        product.stock = new_stock
        self.db.commit()
        self.db.refresh(product)
        return product
    
    def check_stock(self, product_id: int, required_quantity: int) -> bool:
        """Check if product has sufficient stock"""
        product = self.get_by_id(product_id)
        if not product:
            return False
        return product.stock >= required_quantity
    
    def count(self) -> int:
        """Get total count of products"""
        return self.db.query(Product).count()


class ProcessedEventRepository:
    """Repository for tracking processed events (idempotency)"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def is_processed(self, event_id: str) -> bool:
        """Check if event was already processed"""
        return self.db.query(ProcessedEvent).filter(
            ProcessedEvent.event_id == event_id
        ).first() is not None
    
    def mark_processed(self, event_id: str, event_type: str) -> ProcessedEvent:
        """Mark event as processed"""
        processed_event = ProcessedEvent(
            event_id=event_id,
            event_type=event_type
        )
        self.db.add(processed_event)
        self.db.commit()
        self.db.refresh(processed_event)
        return processed_event