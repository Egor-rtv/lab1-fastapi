Лабораторная работа №2: RESTful API + PostgreSQL + Soft Delete
Описание

REST API для управления предметами (items) с использованием FastAPI, PostgreSQL, SQLAlchemy, Alembic.
Технологии

    Python 3.11 / FastAPI

    PostgreSQL 16

    SQLAlchemy (async)

    Alembic (миграции)

    Docker Compose

Функциональность

     CRUD (GET, POST, PUT, PATCH, DELETE)

    Пагинация (page, limit)

     Мягкое удаление (soft delete)

     Валидация через Pydantic

     Миграции Alembic

Запуск

    Клонировать репозиторий:
    bash

    git clone https://github.com/Egor-rtv/lab1-fastapi.git
    cd lab1-fastapi

    Создать .env из примера:
    bash

    cp .env.example .env

    Запустить через Docker Compose:
    bash

    docker-compose up --build

    Открыть Swagger:
    text

    http://localhost:4200/docs

API Endpoints
Метод	URL	Описание
GET	/items	Список с пагинацией
POST	/items	Создать элемент
GET	/items/{id}	Получить по ID
PUT	/items/{id}	Полное обновление
PATCH	/items/{id}	Частичное обновление
DELETE	/items/{id}	Мягкое удаление
Пагинация

    page — страница (по умолч. 1)

    limit — элементов на странице (по умолч. 10, макс. 100)

Примеры запросов

Создать элемент:
bash

curl -X POST http://localhost:4200/items \
  -H "Content-Type: application/json" \
  -d '{"name": "Ноутбук", "description": "Игровой ноутбук"}'

Получить список:
bash

curl "http://localhost:4200/items?page=1&limit=10"

Мягкое удаление:
bash

curl -X DELETE http://localhost:4200/items/1

Структура проекта
text

labi/
├── app/
│   ├── routers/
│   │   └── items.py
│   ├── crud.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   └── main2.py
├── migrations/
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md