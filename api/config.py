from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    anthropic_api_key: str
    deepgram_api_key: str
    twilio_account_sid: str
    twilio_auth_token: str
    stripe_secret_key: str
    stripe_webhook_secret: str
    do_spaces_key: str
    do_spaces_secret: str
    do_spaces_endpoint: str

    class Config:
        env_file = ".env"


settings = Settings()
