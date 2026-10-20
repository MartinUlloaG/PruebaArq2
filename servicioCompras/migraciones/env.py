from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.configuracion import configuracion
from app.infraestructura import modelos  # noqa: F401  (registra las tablas en Base.metadata)
from app.infraestructura.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Alembic compara esta metadata (los modelos) contra la BD real al autogenerar.
target_metadata = Base.metadata

# La URL sale de configuracion.py (que lee el .env), no de alembic.ini,
# para no duplicarla ni dejar la clave escrita en un archivo versionado.
URL = configuracion.url_base_de_datos


def run_migrations_offline() -> None:
    """Modo offline: genera el SQL sin conectarse (alembic upgrade head --sql)."""
    context.configure(
        url=URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Modo normal: se conecta a la BD y aplica las migraciones en una transacción."""
    motor = create_engine(URL, poolclass=pool.NullPool, connect_args={"connect_timeout": 5})
    with motor.connect() as conexion:
        context.configure(connection=conexion, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
