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
    # Login: con 3 claves malas seguidas la cuenta se bloquea un rato (contra fuerza bruta).
    login_intentos_maximos: int = 3
    login_minutos_bloqueo: int = 5

    # Kafka: por aquí viajan los pasos de la Saga. kafka_activo=False apaga los
    # hilos de mensajería (las pruebas que no necesitan broker lo apagan).
    kafka_servidores: str = "127.0.0.1:9092"
    kafka_activo: bool = True
    # TTL de la reserva: si el pago no se resuelve en este tiempo, el stock vuelve.
    # 7 minutos: el comprador tiene ~5 para pagar en la pasarela y el resto es margen
    # para que la confirmación viaje por Kafka.
    segundos_reserva: int = 420
    # La pasarela cierra el pago este margen antes de que venza la reserva. Cubre la
    # ventana que tiene la pasarela para la confirmación (60 s) y lo que tarda el
    # resultado en volver por Kafka. Así no se cobra un pedido cuyo stock ya se devolvió.
    segundos_margen_confirmacion: int = 90
    # Load shedding: como mucho estas compras a la vez tocan la BD. Todas compiten por la
    # misma fila (el stock del producto) y cada una tiene tomada una conexión mientras
    # espera; sin este límite, en un Cyberday se agota el pool y fallan hasta las
    # consultas. El resto espera unos segundos y, si no entra, recibe 503 para reintentar.
    compras_simultaneas: int = 8
    segundos_espera_compra: float = 3
    # Adónde devuelve la pasarela al comprador cuando termina de pagar.
    url_retorno_pago: str = "http://localhost:5173/pago/retorno"

    # MongoDB: el catálogo que se le muestra al cliente (lado de lectura de CQRS).
    mongo_url: str = "mongodb://127.0.0.1:27017"
    mongo_db: str = "tienda"

    # Servicios satélite (procesos aparte). El tiempo límite es corto a propósito.
    recomendaciones_grpc: str = "127.0.0.1:50051"
    recomendaciones_segundos_limite: float = 1

    @property
    def url_base_de_datos(self) -> str:
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


configuracion = Configuracion()
