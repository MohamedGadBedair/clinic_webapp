from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config=SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    # cors
    cors_origins:list[str] = ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"]

    # token secrets
    secret_key:SecretStr
    algorithm:str='HS256'
    access_token_expire_minutes:int=720
    
    # ather needed
    max_upload_size_bytes:int =5*1024*1024
    post_per_page:int = 10
    reset_token_expire_minutes:int = 10
    validate_email_token_expire_minutes:int = 10

    # Google OAuth2 secrets
    google_client_id: str = ""
    google_client_secret: SecretStr = SecretStr("")


    # email secrets
    mail_server: str = "localhost"
    mail_port: int = 587
    mail_username: str = ""
    mail_password: SecretStr = SecretStr("")
    mail_from: str = "noreply@example.com"
    mail_use_tls: bool = True

    frontend_url: str = "http://localhost:8000"
    
    # base database secrets
    db_url:str

    # migration database secrets
    # db_url_migrate:str

    # pooling database secrets
    # db_url_pool:str

        
settings= Settings()