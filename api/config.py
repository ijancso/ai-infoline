from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    deepgram_api_key: Optional[str] = None
    elevenlabs_api_key: str
    telnyx_api_key: str
    telnyx_public_key: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
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
