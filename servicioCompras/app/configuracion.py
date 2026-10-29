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
    # 127.0.0.1 y no "localhost": en Windows "localhost" intenta primero IPv6 (::1),
    # pero el puerto está publicado solo en IPv4, y cada conexión quedaba esperando.
    postgres_host: str = "127.0.0.1"

    # Secreto para firmar los JWT. Obligatorio y sin valor por defecto:
    # si falta, la app no arranca (mejor que arrancar con un secreto débil).
    jwt_secreto: str
    jwt_minutos: int = 30

    # Kafka: por aquí viajan los pasos de la Saga. kafka_activo=False apaga los
    # hilos de mensajería (las pruebas que no necesitan broker lo apagan).
    kafka_servidores: str = "127.0.0.1:9092"
    kafka_activo: bool = True
    # TTL de la reserva: si el pago no se resuelve en este tiempo, el stock vuelve.
    segundos_reserva: int = 60

    # MongoDB: el catálogo que se le muestra al cliente (lado de lectura de CQRS).
    mongo_url: str = "mongodb://127.0.0.1:27017"
    mongo_db: str = "tienda"

    # Servicios satélite (procesos aparte). El tiempo límite es corto a propósito.
    recomendaciones_url: str = "http://127.0.0.1:8002"
    recomendaciones_segundos_limite: float = 1

    @property
    def url_base_de_datos(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


configuracion = Configuracion()
