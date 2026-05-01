from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int = 5432

    redis_host: str
    redis_port: int = 6379

    app_env: str = "development"
    secret_key: str
    auth_username: str = "admin"
    auth_password: str = "sentinel_admin"
    auth_password_hash: str | None = None
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    default_admin_username: str = "admin"
    default_admin_password: str = "admin123"
    access_token_expire_minutes: int = 480

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    class Config:
        env_file = ".env"


settings = Settings()
