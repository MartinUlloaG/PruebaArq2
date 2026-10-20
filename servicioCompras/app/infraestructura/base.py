from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.configuracion import configuracion

# Nombres predecibles para todas las restricciones. Alembic los necesita
# para poder borrarlas o modificarlas en migraciones futuras.
CONVENCION_NOMBRES = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Clase base de todos los modelos."""

    metadata = MetaData(naming_convention=CONVENCION_NOMBRES)


motor = create_engine(
    configuracion.url_base_de_datos,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 5},
)

Sesion = sessionmaker(bind=motor, expire_on_commit=False)
