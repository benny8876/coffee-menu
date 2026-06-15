from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
import models, schemas
from websocket import manager_ws
from typing import List 

router = APIRouter(prefix="/menu", tags=["Menu (Client)"])

@router.get("/", response_model=List[schemas.MenuItemResponse])
def get_available_menu(db: Session = Depends(get_db)):
    # Returns only items currently marked as available
    return db.query(models.MenuItem).filter(models.MenuItem.is_available == True).all()

@router.post("/order", response_model=schemas.OrderResponse, status_code=status.HTTP_201_CREATED)
async def place_order(order_data: schemas.OrderCreate, db: Session = Depends(get_db)):
    # Verify table exists
    table = db.query(models.RestaurantTable).filter(models.RestaurantTable.id == order_data.table_id).first()
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    total_price = 0.0
    db_order = models.Order(table_id=order_data.table_id, status=models.OrderStatus.PENDING)
    db.add(db_order)
    db.flush()  # Generate order ID without committing yet

    # Validate items and calculate prices
    for item in order_data.items:
        menu_item = db.query(models.MenuItem).filter(models.MenuItem.id == item.menu_item_id).first()
        if not menu_item or not menu_item.is_available:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Menu item {item.menu_item_id} is unavailable or does not exist")
        
        item_total = menu_item.price * item.quantity
        total_price += item_total

        db_order_item = models.OrderItem(
            order_id=db_order.id,
            menu_item_id=item.menu_item_id,
            quantity=item.quantity,
            notes=item.notes
        )
        db.add(db_order_item)

    db_order.total_price = total_price
    db.commit()
    db.refresh(db_order)

    # Convert to schema format for serialization before sending via WebSocket
    response_payload = schemas.OrderResponse.model_validate(db_order).model_dump(mode='json')
    
    # Notify kitchen panel in real-time
    await manager_ws.broadcast({"event": "new_order", "order": response_payload})

    return db_order