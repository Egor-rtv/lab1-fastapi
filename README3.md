# Лабораторная работа №3: Авторизация и аутентификация (JWT, OAuth2, Cookies)

## Описание
REST API с системой аутентификации и авторизации, поддержкой JWT токенов, HttpOnly cookies, Refresh Token механизмом и входом через OAuth (Yandex ID).

## Технологии
- Python 3.11 / FastAPI
- PostgreSQL 16
- SQLAlchemy (async) + Alembic
- JWT (PyJWT)
- bcrypt (хеширование паролей с солью)
- OAuth 2.0 (Yandex ID)
- Docker / Docker Compose

## Функциональность
- ✅ Регистрация и вход (email + пароль)
- ✅ JWT токены (Access + Refresh)
- ✅ HttpOnly cookies (защита от XSS)
- ✅ Refresh Token механизм (обновление токенов)
- ✅ Logout / Logout-all (отзыв сессий)
- ✅ Защита ресурсов (требуется авторизация)
- ✅ OAuth 2.0 (Yandex ID) — ручная реализация
- ✅ Хеширование паролей с уникальной солью (bcrypt)

## Эндпоинты Auth

| Метод | URI | Описание |
|-------|-----|----------|
| POST | `/auth/register` | Регистрация нового пользователя |
| POST | `/auth/login` | Вход, установка cookies |
| POST | `/auth/refresh` | Обновление токенов |
| GET | `/auth/whoami` | Информация о текущем пользователе |
| POST | `/auth/logout` | Завершение текущей сессии |
| POST | `/auth/logout-all` | Завершение всех сессий |
| GET | `/auth/oauth/yandex` | Вход через Яндекс |
| GET | `/auth/oauth/yandex/callback` | Callback Яндекса |

## Эндпоинты Items (защищённые)

| Метод | URI | Описание |
|-------|-----|----------|
| GET | `/items` | Список предметов (пагинация) |
| GET | `/items/{id}` | Получить предмет по ID |
| POST | `/items` | Создать предмет |
| PUT | `/items/{id}` | Полное обновление |
| PATCH | `/items/{id}` | Частичное обновление |
| DELETE | `/items/{id}` | Мягкое удаление |

## Запуск

### 1. Клонирование репозитория
```bash
git clone https://github.com/Egor-rtv/lab1-fastapi.git
cd lab1-fastapi/lab3
2. Создание файла .env
bash

cp .env.example .env

Отредактируйте .env, заполнив:

    Данные PostgreSQL

    JWT секреты

    OAuth Client ID и Secret (Yandex)

3. Запуск через Docker Compose
bash

docker-compose up --build

4. Проверка

    Swagger: http://localhost:4200/docs

    API: http://localhost:4200/auth/whoami

Примеры запросов
Регистрация
bash

curl -X POST http://localhost:4200/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "123456"}'

Вход
bash

curl -X POST http://localhost:4200/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "123456"}' \
  -c cookies.txt

Получение списка items (с авторизацией)
bash

curl -X GET http://localhost:4200/items -b cookies.txt

Обновление токенов
bash

curl -X POST http://localhost:4200/auth/refresh -b cookies.txt -c cookies.txt

Выход
bash

curl -X POST http://localhost:4200/auth/logout -b cookies.txt

Выход из всех сессий
bash

curl -X POST http://localhost:4200/auth/logout-all -b cookies.txt

OAuth Яндекс (в браузере)
text

http://localhost:4200/auth/oauth/yandex

Структура проекта
text

lab3/
├── app/
│   ├── routers/
│   │   ├── auth.py          # Эндпоинты аутентификации
│   │   └── items.py         # CRUD ресурсов
│   ├── security/
│   │   ├── hashing.py       # bcrypt (хеширование паролей)
│   │   ├── jwt.py           # JWT токены
│   │   └── cookies.py       # HttpOnly cookies
│   ├── auth/
│   │   └── yandex.py        # OAuth Яндекс (ручная реализация)
│   ├── dependencies.py      # get_current_user()
│   ├── crud.py              # Сервисный слой
│   ├── database.py          # Подключение к БД
│   ├── models.py            # SQLAlchemy модели
│   ├── schemas.py           # Pydantic DTO
│   └── main2.py             # Точка входа
├── migrations/              # Alembic миграции
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md

Безопасность

    ✅ Пароли хешируются с уникальной солью (bcrypt)

    ✅ Access и Refresh токены подписываются разными секретами

    ✅ Refresh Token хранится в БД в хешированном виде

    ✅ Токены передаются через HttpOnly cookies (защита от XSS)

    ✅ SameSite=Lax для защиты от CSRF

    ✅ Параметр state в OAuth (защита от CSRF)

    ✅ Logout и Logout-all отзывают токены в БД