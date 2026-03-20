from fastapi import FastAPI
from datetime import date

app = FastAPI()

def days_until_new_year():
    """Функция для расчета дней до Нового года"""
    today = date.today()
    current_year = today.year
    # Дата Нового года следующего года
    new_year = date(current_year + 1, 1, 1)
    # Разница в днях
    delta = new_year - today
    return delta.days

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/info")
async def get_info():
    """
    Эндпоинт, возвращающий количество дней до Нового года
    """
    days_left = days_until_new_year()
    return {"days_before_new_year": days_left}