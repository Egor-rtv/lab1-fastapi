from fastapi import FastAPI
from app.routers import items, auth
from datetime import date

app = FastAPI(title="Lab2 REST API", version="1.0")

# Подключаем роутеры
app.include_router(items.router)
app.include_router(auth.router)  

@app.get("/")
async def root():
    return {"message": "Lab2 API is running"}

@app.get("/info")
async def get_info():
    today = date.today()
    new_year = date(today.year + 1, 1, 1)
    days_left = (new_year - today).days
    return {"days_before_new_year": days_left}