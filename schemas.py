from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from models import OrderStatus

# --- Menu Schemas ---
class MenuItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    price: float = Field(..., gt=0)
    category: str
    is_available: bool = True

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = None
    is_available: Optional[bool] = None

class MenuItemResponse(MenuItemBase):
    id: int
    class Config:
        from_attributes = True

# --- Order Schemas ---
class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(..., gt=0)
    notes: Optional[str] = None

class OrderCreate(BaseModel):
    table_id: int
    items: List[OrderItemCreate]

class OrderItemResponse(BaseModel):
    id: int
    menu_item: MenuItemResponse
    quantity: int
    notes: Optional[str] = None
    class Config:
        from_attributes = True

class TableResponse(BaseModel):
    id: int
    number: int
    class Config:
        from_attributes = True

class OrderResponse(BaseModel):
    id: int
    table: TableResponse
    status: OrderStatus
    total_price: float
    created_at: datetime
    items: List[OrderItemResponse]
    class Config:
        from_attributes = True

# --- Analytics Schemas ---
class DailyAnalytics(BaseModel):
    date: str
    total_revenue: float
    total_orders_completed: int
    top_selling_items: List[dict]