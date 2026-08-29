from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    cache_ttl_seconds: int = 45
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    ais_api_key: str = ""
    opensky_client_id: str = ""
    opensky_client_secret: str = ""

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
