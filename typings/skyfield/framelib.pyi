from ._typing import FloatArray
from .timelib import Time

class itrs:
    @staticmethod
    def rotation_at(t: Time) -> FloatArray: ...
