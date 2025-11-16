"""
Order Service - Business Logic Layer
"""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.repositories.order_repository import OrderRepository
from app.services.product_client import ProductServiceClient, ProductNotFoundError, ProductServiceUnavailableError
from app.publishers.event_publisher import EventPublisher
from app.schemas.order import OrderCreate, OrderResponse, OrderListResponse


class OrderService:
    """Service layer for order business logic"""
    
    def __init__(self, db: Session):
        self.repository = OrderRepository(db)
        self.product_client = ProductServiceClient()
        self.event_publisher = EventPublisher()
    
    def get_all_orders(self, skip: int = 0, limit: int = 100) -> OrderListResponse:
        """Get all orders with pagination"""
        orders = self.repository.get_all(skip=skip, limit=limit)
        total = self.repository.count()
        
        return OrderListResponse(
            orders=[OrderResponse.model_validate(o) for o in orders],
            total=total
        )
    
    def get_order_by_id(self, order_id: int) -> Optional[OrderResponse]:
        """Get order by ID"""
        order = self.repository.get_by_id(order_id)
        if not order:
            return None
        return OrderResponse.model_validate(order)
    
    def get_orders_by_customer(self, email: str) -> List[OrderResponse]:
        """Get orders by customer email"""
        orders = self.repository.get_by_customer_email(email)
        return [OrderResponse.model_validate(o) for o in orders]
    
    async def create_order(self, order_data: OrderCreate) -> OrderResponse:
        """
        Create new order
        
        Steps:
        1. Validate input
        2. Call Product Service to get product info (sync)
        3. Check stock availability
        4. Calculate total price
        5. Save order to database
        6. Publish OrderCreated event to RabbitMQ
        7. Return order response
        
        Args:
            order_data: Order creation data
        
        Returns:
            Created order
        
        Raises:
            ProductNotFoundError: If product not found
            ProductServiceUnavailableError: If Product Service unavailable
            ValueError: If insufficient stock
        """
        # Step 1: Get product info from Product Service (sync call)
        try:
            product = await self.product_client.get_product(order_data.product_id)
        except ProductNotFoundError as e:
            raise ValueError(f"Product not found: {e}")
        except ProductServiceUnavailableError as e:
            raise RuntimeError(f"Product Service unavailable: {e}")
        
        # Step 2: Check stock availability
        try:
            has_stock = await self.product_client.check_stock(
                order_data.product_id,
                order_data.quantity
            )
            if not has_stock:
                raise ValueError(
                    f"Insufficient stock. Product ID: {order_data.product_id}, "
                    f"Requested: {order_data.quantity}, Available: {product.get('stock', 0)}"
                )
        except ProductServiceUnavailableError as e:
            raise RuntimeError(f"Cannot verify stock: {e}")
        
        # Step 3: Calculate total price
        unit_price = product['price']
        total_price = unit_price * order_data.quantity
        
        # Step 4: Save order to database
        order_dict = {
            'product_id': order_data.product_id,
            'product_name': product['name'],
            'quantity': order_data.quantity,
            'unit_price': unit_price,
            'total_price': total_price,
            'status': 'pending',
            'customer_email': order_data.customer_email
        }
        
        order = self.repository.create(order_dict)
        
        # Step 5: Publish OrderCreated event
        event_data = {
            'order_id': order.id,
            'product_id': order.product_id,
            'product_name': order.product_name,
            'quantity': order.quantity,
            'unit_price': order.unit_price,
            'total_price': order.total_price,
            'customer_email': order.customer_email,
            'status': order.status
        }
        
        # Try to publish event (non-blocking)
        try:
            self.event_publisher.publish_order_created(event_data)
        except Exception as e:
            # Log error but don't fail the order creation
            print(f"Warning: Failed to publish OrderCreated event: {e}")
            # In production, save to outbox table for retry
        
        return OrderResponse.model_validate(order)
    
    def update_order_status(self, order_id: int, new_status: str) -> Optional[OrderResponse]:
        """
        Update order status
        
        Args:
            order_id: Order ID
            new_status: New status value
        
        Returns:
            Updated order or None if not found
        """
        order = self.repository.update_status(order_id, new_status)
        if not order:
            return None
        
        # Publish OrderStatusChanged event
        event_data = {
            'order_id': order.id,
            'old_status': 'pending',  # In real app, track old status
            'new_status': order.status,
            'updated_at': order.updated_at.isoformat()
        }
        
        try:
            self.event_publisher.publish_order_status_changed(event_data)
        except Exception as e:
            print(f"Warning: Failed to publish OrderStatusChanged event: {e}")
        
        return OrderResponse.model_validate(order)