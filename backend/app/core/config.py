from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",  # ignora variáveis no .env que não existem no modelo (ex.: ZAPI_* removidas)
    )

    # Banco de Dados
    DATABASE_URL: str
    DATABASE_SCHEMA: str = "public"

    # JWT
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 horas

    # Cotação
    AWESOME_API_URL: str = "https://economia.awesomeapi.com.br/json/last/USD-BRL"

    # CORS (produção: lista separada por vírgula, ex: "https://subs.nitrofund.com")
    CORS_ORIGINS: str = ""

    # Timezone para determinação do "mês atual" (validações, dashboard)
    # Padrão: America/Sao_Paulo (Brasil)
    APP_TIMEZONE: str = "America/Sao_Paulo"


settings = Settings()