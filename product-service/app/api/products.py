"""
Product API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.services.product_service import ProductService
from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
    StockUpdate,
    ProductResponse,
    ProductListResponse,
    StockCheckResponse
)

router = APIRouter(prefix="/products", tags=["products"])


def get_product_service(db: Session = Depends(get_db)) -> ProductService:
    """Dependency to get ProductService instance"""
    return ProductService(db)


@router.get("", response_model=ProductListResponse, summary="Get all products")
def get_products(
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of products to return"),
    service: ProductService = Depends(get_product_service)
):
    """
    Retrieve all products with pagination
    
    - **skip**: Number of products to skip (default: 0)
    - **limit**: Maximum number of products to return (default: 100, max: 1000)
    """
    return service.get_all_products(skip=skip, limit=limit)


@router.get("/{product_id}", response_model=ProductResponse, summary="Get product by ID")
def get_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    """
    Retrieve a specific product by ID
    
    - **product_id**: Product ID
    """
    product = service.get_product_by_id(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id={product_id} not found"
        )
    return product


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED, summary="Create product")
def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(get_product_service)
):
    """
    Create a new product
    
    - **name**: Product name (required)
    - **description**: Product description (optional)
    - **price**: Product price (required, must be positive)
    - **stock**: Stock quantity (required, must be non-negative)
    - **category**: Product category (optional)
    - **image_url**: Product image URL (optional)
    """
    return service.create_product(product_data)


@router.put("/{product_id}", response_model=ProductResponse, summary="Update product")
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    service: ProductService = Depends(get_product_service)
):
    """
    Update an existing product
    
    All fields are optional. Only provided fields will be updated.
    
    - **product_id**: Product ID
    """
    product = service.update_product(product_id, product_data)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id={product_id} not found"
        )
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete product")
def delete_product(
    product_id: int,
    service: ProductService = Depends(get_product_service)
):
    """
    Delete a product
    
    - **product_id**: Product ID
    """
    success = service.delete_product(product_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Product with id={product_id} not found"
        )
    return None


@router.patch("/{product_id}/stock", response_model=ProductResponse, summary="Update product stock")
def update_stock(
    product_id: int,
    stock_data: StockUpdate,
    service: ProductService = Depends(get_product_service)
):
    """
    Update product stock by adding or subtracting quantity
    
    - **product_id**: Product ID
    - **quantity**: Quantity to add (positive) or subtract (negative)
    
    Example: {"quantity": -5} will subtract 5 from current stock
    """
    try:
        product = service.update_stock(product_id, stock_data.quantity)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id={product_id} not found"
            )
        return product
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )


@router.get("/{product_id}/check", response_model=StockCheckResponse, summary="Check stock availability")
def check_stock(
    product_id: int,
    quantity: int = Query(1, ge=1, description="Required quantity"),
    service: ProductService = Depends(get_product_service)
):
    """
    Check if product has sufficient stock
    
    - **product_id**: Product ID
    - **quantity**: Required quantity (default: 1)
    """
    return service.check_stock(product_id, quantity)