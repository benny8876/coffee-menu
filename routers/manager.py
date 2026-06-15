from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, time
from database import get_db
import models, schemas
from typing import List 

router = APIRouter(prefix="/manager", tags=["Manager Panel"])

# --- Menu Management ---
@router.post("/menu", response_model=schemas.MenuItemResponse)
def create_menu_item(item: schemas.MenuItemCreate, db: Session = Depends(get_db)):
    db_item = models.MenuItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/menu/{item_id}", response_model=schemas.MenuItemResponse)
def update_menu_item(item_id: int, updated_item: schemas.MenuItemUpdate, db: Session = Depends(get_db)):
    db_item = db.query(models.MenuItem).filter(models.MenuItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Menu item not found")
    
    for key, value in updated_item.model_dump(exclude_unset=True).items():
        setattr(db_item, key, value)
        
    db.commit()
    db.refresh(db_item)
    return db_item

# --- Order & Receipt Management ---
@router.get("/orders", response_model=List[schemas.OrderResponse])
def get_all_orders(db: Session = Depends(get_db)):
    # Returns history of all orders for oversight
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()

@router.get("/orders/{order_id}/voucher")
def print_voucher(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Generate a formatted dictionary mimicking a printed paper voucher
    voucher_data = {
        "restaurant_name": "QR Dine Inn",
        "voucher_id": f"REC-{order.id:06d}",
        "timestamp": order.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        "table_number": order.table.number,
        "items": [
            {
                "name": item.menu_item.name,
                "quantity": item.quantity,
                "unit_price": item.menu_item.price,
                "subtotal": item.quantity * item.menu_item.price
            } for item in order.items
        ],
        "subtotal": order.total_price,
        "tax_amount": round(order.total_price * 0.10, 2),  # Example 10% tax
        "grand_total": round(order.total_price * 1.10, 2),
        "status": order.status.value
    }
    return voucher_data

# --- Daily Analytics ---
@router.get("/analytics/daily", response_model=schemas.DailyAnalytics)
def get_daily_analytics(db: Session = Depends(get_db)):
    today_start = datetime.combine(datetime.today(), time.min)
    today_end = datetime.combine(datetime.today(), time.max)

    # Get completed orders for today
    today_orders = db.query(models.Order).filter(
        models.Order.created_at.between(today_start, today_end),
        models.Order.status == models.OrderStatus.COMPLETED
    ).all()

    total_revenue = sum(order.total_price for order in today_orders)
    total_completed = len(today_orders)

    # Aggregated item sales counts
    popular_items = db.query(
        models.MenuItem.name,
        func.sum(models.OrderItem.quantity).label("total_sold")
    ).join(models.OrderItem, models.MenuItem.id == models.OrderItem.menu_item_id)\
     .join(models.Order, models.Order.id == models.OrderItem.order_id)\
     .filter(
         models.Order.created_at.between(today_start, today_end),
         models.Order.status == models.OrderStatus.COMPLETED
     ).group_by(models.MenuItem.name)\
     .order_by(func.sum(models.OrderItem.quantity).desc())\
     .limit(5).all()

    top_selling = [{"name": item[0], "sold_qty": item[1]} for item in popular_items]

    return schemas.DailyAnalytics(
        date=datetime.today().strftime("%Y-%m-%d"),
        total_revenue=total_revenue,
        total_orders_completed=total_completed,
        top_selling_items=top_selling
    )