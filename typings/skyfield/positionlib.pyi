from typing import Protocol

from ._typing import FloatArray, Numeric
from .timelib import Time
from .units import Angle, Distance, Velocity

class _Frame(Protocol):
    def rotation_at(self, t: Time) -> FloatArray: ...

class ICRF[T: Numeric = Numeric]:
    position: Distance[FloatArray]
    velocity: Velocity[FloatArray]
    message: str | None | list[str | None]
    def altaz(self) -> tuple[Angle[T], Angle[T], Distance[T]]: ...
    def frame_xyz(self, frame: _Frame) -> Distance[FloatArray]: ...

class Geocentric[T: Numeric = Numeric](ICRF[T]): ...
