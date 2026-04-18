from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from pydantic_settings import BaseSettings

# Настройки из переменных окружения
class Settings(BaseSettings):
    # PostgreSQL
    DB_HOST: str = "localhost"
    DB_PORT: int = 5432
    DB_USER: str = "student"
    DB_PASSWORD: str = "student_secure_password"
    DB_NAME: str = "lab_db"
    
    # JWT
    jwt_access_secret: str
    jwt_refresh_secret: str
    jwt_access_expiration: int = 15
    jwt_refresh_expiration: int = 10080
    
    # OAuth Yandex
    yandex_client_id: str
    yandex_client_secret: str
    yandex_redirect_uri: str
    
    @property
    def DATABASE_URL(self):
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
    
    class Config:
        env_file = ".env"
        extra = "ignore"


# Создаём экземпляр настроек
settings = Settings()

# Создаём асинхронный движок для работы с БД
engine = create_async_engine(settings.DATABASE_URL, echo=True)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

# Базовый класс для моделей
Base = declarative_base()

# Функция для получения сессии в эндпоинтах
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session