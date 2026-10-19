from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# C:\comercio (dos niveles sobre este archivo: app -> servicioCompras -> comercio)
RAIZ = Path(__file__).resolve().parents[2]


class Configuracion(BaseSettings):
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_port: int = 5440
    postgres_host: str = "localhost"

    @property
    def url_base_de_datos(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


configuracion = Configuracion()