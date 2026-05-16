import os
from fastapi import FastAPI
from app.routers import items, auth
from datetime import date

# Получаем режим работы
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Условное создание приложения
if ENVIRONMENT == "production":
    app = FastAPI(
        title="Lab Project API",
        description="...",
        version="1.0.0",
        docs_url=None,      # отключаем Swagger
        redoc_url=None,     # отключаем ReDoc
        openapi_url=None    # отключаем OpenAPI JSON
    )
else:
    app = FastAPI(
        title="Lab Project API",
        description="...",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

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