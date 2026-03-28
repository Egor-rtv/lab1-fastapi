# Лабораторная работа 1: Клиент-серверное взаимодействие

## Описание
Веб-приложение на FastAPI, которое возвращает количество дней до Нового года.

## Технологии
- Python 3.11
- FastAPI
- Docker

## Структура проекта
lab1-fastapi/
├── Dockerfile
├── .dockerignore
├── .gitignore
├── requirements.txt
├── README.md
└── main.py
## Запуск приложения

### 1. Клонирование репозитория
```bash
git clone https://github.com/Egor-rtv/lab1-fastapi.git
cd lab1-fastapi
2. Запуск через Docker
```
Собрать образ:
bash

docker build -t lab1-fastapi .

Запустить контейнер:
bash

docker run -p 4200:4200 lab1-fastapi

3. Проверка работы

Открыть в браузере: http://localhost:4200/info

Ожидаемый ответ:
json

{
    "days_before_new_year": 123
}