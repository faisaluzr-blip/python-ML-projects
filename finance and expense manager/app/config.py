from functools import lru_cache
from pathlib import Path
from pydantic import BaseModel
from pydantic_settings import BaseSettings


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    app_name: str = "Finance Intelligence Platform"
    database_url: str = f"sqlite:///{BASE_DIR / 'finance.db'}"
    jwt_secret: str = "change-this-secret-in-production"
    jwt_expire_minutes: int = 60 * 24
    currency_api_base: str = "local"
    notification_email_from: str = "alerts@finance.local"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


class CurrencyRate(BaseModel):
    code: str
    symbol: str
    rate_to_usd: float


CURRENCIES = {
    "USD": CurrencyRate(code="USD", symbol="$", rate_to_usd=1.0),
    "INR": CurrencyRate(code="INR", symbol="₹", rate_to_usd=83.2),
    "EUR": CurrencyRate(code="EUR", symbol="€", rate_to_usd=0.92),
    "GBP": CurrencyRate(code="GBP", symbol="£", rate_to_usd=0.79),
    "AED": CurrencyRate(code="AED", symbol="د.إ", rate_to_usd=3.67),
    "JPY": CurrencyRate(code="JPY", symbol="¥", rate_to_usd=154.0),
}


@lru_cache
def get_settings() -> Settings:
    return Settings()
