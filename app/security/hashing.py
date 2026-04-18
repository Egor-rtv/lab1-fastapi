import bcrypt
from typing import Tuple


def hash_password(password: str) -> str:
    """
    Хеширует пароль с автоматической генерацией соли.
    Возвращает строку с хешем (bcrypt сохраняет соль внутри).
    """
    # Генерируем соль и хешируем пароль
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли введённый пароль сохранённому хешу.
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )