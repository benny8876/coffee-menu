import enum
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    PREPARING = "preparing"
    SERVED = "served"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class RestaurantTable(Base):
    __tablename__ = "tables"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(Integer, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)

class MenuItem(Base):
    __tablename__ = "menu_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # e.g., Appetizer, Main, Drink
    is_available = Column(Boolean, default=True)

class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    table_id = Column(Integer, ForeignKey("tables.id"), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    total_price = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    table = relationship("RestaurantTable")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    menu_item_id = Column(Integer, ForeignKey("menu_items.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    notes = Column(String, nullable=True)  # e.g., "No onions", "Extra spicy"

    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem")