from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Wartości, które nie mogą trafić na produkcję.
WEAK_ADMIN_TOKENS = {"", "change-me", "change-me-admin", "admin", "secret"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # --- API ---
    PROJECT_NAME: str = "Weather API"
    VERSION: str = "1.0.0"

    # --- Server ---
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    # Dokumentacja OpenAPI (/docs, /redoc, /openapi.json) — domyślnie wyłączona
    # na produkcji (mniej pamięci i mniejsza powierzchnia ataku).
    ENABLE_DOCS: bool = False
    # Limit równoczesnych połączeń obsługiwanych przez serwer (ochrona małego VPS).
    LIMIT_CONCURRENCY: int = 50

    # --- Database ---
    DB_USER: str = "weatherapi"
    DB_PASS: str = "change-me"
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_NAME: str = "weather_stations"
    # Jedno stanowisko → mała pula wystarcza.
    DB_POOL_SIZE: int = 2
    DB_MAX_OVERFLOW: int = 0
    # Opcjonalne pełne URL-e (nadpisują pola DB_* powyżej).
    # Przykład lekkiej bazy bez serwera MySQL: sqlite+aiosqlite:////opt/weatherapi/weather.db
    DATABASE_URL: str | None = None
    DATABASE_URL_SYNC: str | None = None

    # --- Auth ---
    ADMIN_TOKEN: str = "change-me-admin"
    # Tylko do testów/dev: zezwala na słaby ADMIN_TOKEN.
    ALLOW_INSECURE_DEFAULTS: bool = False

    # --- Rate limiting (per klucz stacji / IP) ---
    RATE_LIMIT_PER_MIN: int = 120

    # --- Limity żądań ---
    MAX_BODY_BYTES: int = 65_536

    # --- Command lifecycle ---
    COMMAND_TTL_MINUTES: int = 60
    MAX_ACTIVE_COMMANDS_PER_STATION: int = 1

    @model_validator(mode="after")
    def _validate_admin_token(self) -> "Settings":
        if self.ALLOW_INSECURE_DEFAULTS:
            return self
        if self.ADMIN_TOKEN in WEAK_ADMIN_TOKENS or len(self.ADMIN_TOKEN) < 16:
            raise ValueError(
                "ADMIN_TOKEN jest domyślny lub zbyt krótki (min. 16 znaków). "
                "Ustaw silny sekret w .env lub ustaw ALLOW_INSECURE_DEFAULTS=true do testów."
            )
        return self

    @property
    def sync_db_url(self) -> str:
        if self.DATABASE_URL_SYNC:
            return self.DATABASE_URL_SYNC
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )

    @property
    def async_db_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+aiomysql://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
