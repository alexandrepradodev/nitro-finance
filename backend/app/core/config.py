from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Banco de dados
    DATABASE_URL: str

    #JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES = int = 1440

   # Z-API (WhatsApp)
    ZAPI_INSTANCE_ID: str = ""
    ZAPI_TOKEN: str = ""
    ZAPI_PHONE: str = ""

    # Cotação
    AWESOME_API_URL: str = "https://economia.awesomeapi.com.br/json/last/USD-BRL"

    class config:
        env_file = ".env"

settings = Settings()