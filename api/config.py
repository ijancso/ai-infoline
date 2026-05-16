from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    deepgram_api_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    stripe_secret_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None
    do_spaces_key: str
    do_spaces_secret: str
    do_spaces_endpoint: str
    do_spaces_bucket: str
    admin_api_key: str

    class Config:
        env_file = ".env"


settings = Settings()
