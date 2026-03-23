from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "AgentHome"
    APP_VERSION: str = "1.0.0"
    
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    
    DATABASE_URL: str = "sqlite:///./data/database.db"
    
    UPLOAD_DIR: str = "./data/uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024
    
    CORS_ORIGINS: list = ["*"]
    
    DEFAULT_MODEL: str = "gpt-3.5-turbo"
    DEFAULT_TEMPERATURE: float = 0.7
    DEFAULT_MAX_TOKENS: int = 2048
    
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_API_BASE: Optional[str] = None
    
    LOCAL_MODEL_PATH: Optional[str] = None
    
    EMBEDDING_API_KEY: Optional[str] = None
    RERANK_API_KEY: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
