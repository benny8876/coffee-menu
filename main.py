from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import models
from database import engine, SessionLocal
from routers import menu, kitchen, manager
import os 




# Autocreate schema tables for SQLite local database
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="QR Restaurant Ordering System",
    description="Backend service containing Menu, Kitchen and Manager modules with real-time updates."
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Routers
app.include_router(menu.router, prefix="/api/v1")
app.include_router(kitchen.router, prefix="/api/v1")
app.include_router(manager.router, prefix="/api/v1")

@app.on_event("startup")
def seed_initial_data():
    db = SessionLocal()
    # Seed tables if they do not exist
    if not db.query(models.RestaurantTable).first():
        tables = [models.RestaurantTable(number=i) for i in range(1, 11)]
        db.add_all(tables)
        
    # Seed default Menu Items if empty
    if not db.query(models.MenuItem).first():
        items = [
            models.MenuItem(name="Americano", description="Great Taste", price=5000, category="Coffee", is_available=True),
            models.MenuItem(name="Cappuccino", description="With Custom Design", price=6000, category="Coffee", is_available=True),
            models.MenuItem(name="Coffee Latte", description="Latte is good", price=6000, category="Coffee", is_available=True),
            models.MenuItem(name="Espresso", description="High Caffine", price=7000, category="Coffee", is_available=True),
            models.MenuItem(name="French Fries", description="Love taste", price=7000, category="Food", is_available=True),
            models.MenuItem(name="Banana Bread", description="Sweet taste", price=4000, category="Food", is_available=True),
            models.MenuItem(name="Almod Roll", description="SS tier", price=7000, category="Food", is_available=True),
            models.MenuItem(name="Black Tea", description="Alcohol ", price=4000, category="Tea", is_available=True),
            models.MenuItem(name="Green Tea", description="Green Leaf", price=8000, category="Tea", is_available=True),
            models.MenuItem(name="Milke Tea", description="Tea for Single", price=7000, category="Tea", is_available=True),
            models.MenuItem(name="Jasmine Tea", description="Tea for lovers", price=5000, category="Tea", is_available=True),
        ]
        db.add_all(items)
    db.commit()
    db.close()

@app.get("/")
def serve_menu():
    file_path = os.path.join("templates", "menu.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "menu.html not found in static folder"}

@app.get("/kitchen")
def serve_kitchen():
    file_path = os.path.join("templates", "kitchen.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "kitchen.html not found in static folder"}

@app.get("/manager")
def serve_manager():
    file_path = os.path.join("templates", "manager.html")
    if os.path.exists(file_path):
        return FileResponse(file_path)
    return {"error": "manager.html not found in static folder"}