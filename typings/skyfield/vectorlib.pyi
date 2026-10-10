from ._typing import Numeric
from .positionlib import ICRF
from .timelib import Time

class VectorFunction:
    def at[T: Numeric](self, t: Time[T]) -> ICRF[T]: ...
    def __sub__(self, other: VectorFunction) -> VectorFunction: ...
