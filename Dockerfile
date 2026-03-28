FROM python:3.11-slim

WORKDIR /app

# Устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Указываем Python путь к модулям
ENV PYTHONPATH=/app

# Ждём базу, применяем миграции, запускаем приложение
CMD sh -c "alembic upgrade head && uvicorn app.main2:app --host 0.0.0.0 --port 4200"