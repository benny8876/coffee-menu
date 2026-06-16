from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, time, date as date_type
from typing import Optional, List
import csv
import io

from database import get_db
import models, schemas

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
    return db.query(models.Order).order_by(models.Order.created_at.desc()).all()

@router.get("/orders/{order_id}/voucher")
def print_voucher(order_id: int, db: Session = Depends(get_db)):
    order = db.query(models.Order).filter(models.Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

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
        "tax_amount": round(order.total_price * 0.10, 2),
        "grand_total": round(order.total_price * 1.10, 2),
        "status": order.status.value
    }
    return voucher_data

# --- Historical Daily Analytics ---
@router.get("/analytics/daily", response_model=schemas.DailyAnalytics)
def get_daily_analytics(date: Optional[str] = None, db: Session = Depends(get_db)):
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = datetime.today().date()

    day_start = datetime.combine(target_date, time.min)
    day_end = datetime.combine(target_date, time.max)

    # Get completed orders for selected date
    completed_orders = db.query(models.Order).filter(
        models.Order.created_at.between(day_start, day_end),
        models.Order.status == models.OrderStatus.COMPLETED
    ).all()

    total_revenue = sum(order.total_price for order in completed_orders)
    total_completed = len(completed_orders)

    # Aggregated item sales counts for selected date
    popular_items = db.query(
        models.MenuItem.name,
        func.sum(models.OrderItem.quantity).label("total_sold")
    ).join(models.OrderItem, models.MenuItem.id == models.OrderItem.menu_item_id)\
     .join(models.Order, models.Order.id == models.OrderItem.order_id)\
     .filter(
         models.Order.created_at.between(day_start, day_end),
         models.Order.status == models.OrderStatus.COMPLETED
     ).group_by(models.MenuItem.name)\
     .order_by(func.sum(models.OrderItem.quantity).desc())\
     .limit(5).all()

    top_selling = [{"name": item[0], "sold_qty": item[1]} for item in popular_items]

    return schemas.DailyAnalytics(
        date=target_date.strftime("%Y-%m-%d"),
        total_revenue=total_revenue,
        total_orders_completed=total_completed,
        top_selling_items=top_selling
    )

# --- Excel (CSV) Report Export ---
@router.get("/analytics/export")
def export_daily_report(date: Optional[str] = None, db: Session = Depends(get_db)):
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    else:
        target_date = datetime.today().date()

    day_start = datetime.combine(target_date, time.min)
    day_end = datetime.combine(target_date, time.max)

    # Retrieve all orders for the target date range
    orders = db.query(models.Order).filter(
        models.Order.created_at.between(day_start, day_end)
    ).order_by(models.Order.created_at.asc()).all()

    # Generate an in-memory CSV string stream
    output = io.StringIO()
    writer = csv.writer(output)

    # Spreadsheet Headers
    writer.writerow(["Order ID", "Table Number", "Order Time", "Status", "Items Summary", "Revenue Generated ($)"])

    for order in orders:
        # Format the ordered items cleanly: e.g. "Cheeseburger (x2); French Fries (x1)"
        items_summary = "; ".join([f"{item.menu_item.name} (x{item.quantity})" for item in order.items])
        
        writer.writerow([
            order.id,
            order.table.number,
            order.created_at.strftime("%H:%M:%S"),
            order.status.value,
            items_summary,
            f"{order.total_price:.2f}"
        ])

    output.seek(0)
    
    # Send CSV stream response directly to the browser
    filename = f"sales_report_{target_date.strftime('%Y-%m-%d')}.csv"
    headers = {
        'Content-Disposition': f'attachment; filename="{filename}"'
    }
    return StreamingResponse(output, media_type="text/csv", headers=headers)