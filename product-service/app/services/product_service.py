"""
Product Service - Business Logic Layer
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.product_repository import ProductRepository, ProcessedEventRepository
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    StockCheckResponse
)
from app.models.product import Product


class ProductService:
    """Service layer for product business logic"""
    
    def __init__(self, db: Session):
        self.repository = ProductRepository(db)
        self.event_repository = ProcessedEventRepository(db)
    
    def get_all_products(self, skip: int = 0, limit: int = 100) -> ProductListResponse:
        """Get all products with pagination"""
        products = self.repository.get_all(skip=skip, limit=limit)
        total = self.repository.count()
        
        return ProductListResponse(
            products=[ProductResponse.model_validate(p) for p in products],
            total=total
        )
    
    def get_product_by_id(self, product_id: int) -> Optional[ProductResponse]:
        """Get product by ID"""
        product = self.repository.get_by_id(product_id)
        if not product:
            return None
        return ProductResponse.model_validate(product)
    
    def create_product(self, product_data: ProductCreate) -> ProductResponse:
        """Create new product"""
        product = self.repository.create(product_data)
        return ProductResponse.model_validate(product)
    
    def update_product(self, product_id: int, product_data: ProductUpdate) -> Optional[ProductResponse]:
        """Update existing product"""
        product = self.repository.update(product_id, product_data)
        if not product:
            return None
        return ProductResponse.model_validate(product)
    
    def delete_product(self, product_id: int) -> bool:
        """Delete product"""
        return self.repository.delete(product_id)
    
    def update_stock(self, product_id: int, quantity_change: int) -> Optional[ProductResponse]:
        """
        Update product stock
        
        Args:
            product_id: Product ID
            quantity_change: Positive to add, negative to subtract
        
        Returns:
            Updated product or None
        
        Raises:
            ValueError: If resulting stock would be negative
        """
        try:
            product = self.repository.update_stock(product_id, quantity_change)
            if not product:
                return None
            return ProductResponse.model_validate(product)
        except ValueError as e:
            raise e
    
    def check_stock(self, product_id: int, required_quantity: int = 1) -> StockCheckResponse:
        """Check if product has sufficient stock"""
        product = self.repository.get_by_id(product_id)
        
        if not product:
            return StockCheckResponse(
                product_id=product_id,
                available=False,
                stock=0,
                message="Product not found"
            )
        
        available = product.stock >= required_quantity
        message = None if available else f"Insufficient stock. Available: {product.stock}, Required: {required_quantity}"
        
        return StockCheckResponse(
            product_id=product_id,
            available=available,
            stock=product.stock,
            message=message
        )
    
    def process_order_created_event(self, event_data: dict) -> bool:
        """
        Process OrderCreated event from RabbitMQ
        
        Args:
            event_data: Event data containing event_id, order_id, product_id, quantity
        
        Returns:
            True if processed successfully, False otherwise
        """
        event_id = event_data.get("event_id")
        
        # Check idempotency
        if self.event_repository.is_processed(event_id):
            print(f"Event {event_id} already processed. Skipping.")
            return True
        
        # Extract order data
        order_data = event_data.get("data", {})
        product_id = order_data.get("product_id")
        quantity = order_data.get("quantity")
        
        if not product_id or not quantity:
            print(f"Invalid event data: {event_data}")
            return False
        
        try:
            # Update stock (subtract quantity)
            product = self.repository.update_stock(product_id, -quantity)
            
            if not product:
                print(f"Product {product_id} not found")
                return False
            
            # Mark event as processed
            self.event_repository.mark_processed(event_id, event_data.get("event_type", "OrderCreated"))
            
            print(f"✓ Stock updated for product {product_id}: {product.stock + quantity} → {product.stock}")
            return True
            
        except ValueError as e:
            print(f"✗ Error updating stock: {e}")
            return False
        except Exception as e:
            print(f"✗ Unexpected error processing event: {e}")
            return False