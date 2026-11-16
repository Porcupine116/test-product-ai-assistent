from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openrouter_api_key: str = ""

    openrouter_model: str = "openai/gpt-6-luna"

    openrouter_proxy: str = ""

    openrouter_site_url: str = "http://localhost:8000"
    openrouter_app_name: str = "Product AI Assistant"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()