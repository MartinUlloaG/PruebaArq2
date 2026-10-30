import threading
import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

CERRADO = "cerrado"
ABIERTO = "abierto"
SEMIABIERTO = "semiabierto"


class CircuitoAbierto(Exception):
    """El circuito está abierto: no se intentó la llamada."""


class CircuitBreaker:
    def __init__(
        self,
        nombre: str,
        umbral_fallas: int = 3,
        segundos_abierto: float = 10,
        reloj: Callable[[], float] = time.monotonic,  # se reemplaza en las pruebas
    ):
        self.nombre = nombre
        self.umbral_fallas = umbral_fallas
        self.segundos_abierto = segundos_abierto
        self._reloj = reloj
        self._candado = threading.Lock()  # FastAPI atiende varias solicitudes en paralelo
        self._estado = CERRADO
        self._fallas_seguidas = 0
        self._abierto_desde = 0.0
        self._prueba_en_curso = False

    @property
    def estado(self) -> str:
        with self._candado:
            return self._estado_actual()

    def llamar(self, funcion: Callable[..., T], *args, **kwargs) -> T:
        with self._candado:
            estado = self._estado_actual()
            if estado == ABIERTO or (estado == SEMIABIERTO and self._prueba_en_curso):
                raise CircuitoAbierto(f"Circuito abierto hacia {self.nombre}.")
            if estado == SEMIABIERTO:
                self._prueba_en_curso = True  # solo una llamada de prueba a la vez

        try:
            resultado = funcion(*args, **kwargs)
        except Exception:
            self._registrar_falla()
            raise
        self._registrar_exito()
        return resultado

    def _estado_actual(self) -> str:
        # Abierto pasa a semiabierto solo por tiempo: no hace falta un temporizador aparte.
        if self._estado == ABIERTO and self._reloj() - self._abierto_desde >= self.segundos_abierto:
            self._estado = SEMIABIERTO
        return self._estado

    def _registrar_falla(self) -> None:
        with self._candado:
            self._prueba_en_curso = False
            self._fallas_seguidas += 1
            if self._estado == SEMIABIERTO or self._fallas_seguidas >= self.umbral_fallas:
                self._estado = ABIERTO
                self._abierto_desde = self._reloj()

    def _registrar_exito(self) -> None:
        with self._candado:
            self._prueba_en_curso = False
            self._fallas_seguidas = 0
            self._estado = CERRADO
