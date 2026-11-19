"""应用配置（pydantic-settings 从 .env 加载）。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "绿色低碳智慧管控系统"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+asyncpg://smartdocs:smartdocs@localhost:5433/green_carbon"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://smartdocs:smartdocs@localhost:5433/green_carbon"

    JWT_SECRET_KEY: str = "green-carbon-secret-key-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 720

    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # 图形验证码开关：开发环境可设为 false 跳过验证码
    CAPTCHA_ENABLED: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
