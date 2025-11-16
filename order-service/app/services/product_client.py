"""
HTTP Client for Product Service with retry logic
"""
import httpx
from typing import Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config import settings


class ProductServiceError(Exception):
    """Base exception for Product Service errors"""
    pass


class ProductNotFoundError(ProductServiceError):
    """Product not found"""
    pass


class ProductServiceUnavailableError(ProductServiceError):
    """Product Service is unavailable"""
    pass


class InsufficientStockError(ProductServiceError):
    """Insufficient stock"""
    pass


class ProductServiceClient:
    """Client for communicating with Product Service"""
    
    def __init__(self):
        self.base_url = settings.PRODUCT_SERVICE_URL
        self.timeout = 5.0  # 5 seconds timeout
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.RETRY_DELAY, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def get_product(self, product_id: int) -> Optional[Dict]:
        """
        Get product by ID from Product Service
        
        Args:
            product_id: Product ID
        
        Returns:
            Product data or None
        
        Raises:
            ProductNotFoundError: If product not found
            ProductServiceUnavailableError: If service is unavailable
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/products/{product_id}")
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    raise ProductNotFoundError(f"Product {product_id} not found")
                else:
                    raise ProductServiceError(f"Unexpected status code: {response.status_code}")
        
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            print(f"Error calling Product Service: {e}")
            raise ProductServiceUnavailableError(f"Product Service unavailable: {e}")
    
    @retry(
        stop=stop_after_attempt(settings.MAX_RETRIES),
        wait=wait_exponential(multiplier=settings.RETRY_DELAY, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
        reraise=True
    )
    async def check_stock(self, product_id: int, quantity: int) -> bool:
        """
        Check if product has sufficient stock
        
        Args:
            product_id: Product ID
            quantity: Required quantity
        
        Returns:
            True if sufficient stock, False otherwise
        
        Raises:
            ProductNotFoundError: If product not found
            ProductServiceUnavailableError: If service is unavailable
        """
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    f"{self.base_url}/products/{product_id}/check",
                    params={"quantity": quantity}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("available", False)
                elif response.status_code == 404:
                    raise ProductNotFoundError(f"Product {product_id} not found")
                else:
                    raise ProductServiceError(f"Unexpected status code: {response.status_code}")
        
        except (httpx.TimeoutException, httpx.ConnectError) as e:
            print(f"Error calling Product Service: {e}")
            raise ProductServiceUnavailableError(f"Product Service unavailable: {e}")