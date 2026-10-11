from collections.abc import Mapping
from typing import Self

import numpy as np
from numpy.typing import NDArray
from sgp4.api import Satrec

from ._typing import Numeric
from .positionlib import Geocentric
from .timelib import Time, Timescale
from .toposlib import GeographicPosition
from .vectorlib import VectorFunction

class EarthSatellite(VectorFunction):
    epoch: Time[float]
    model: Satrec
    @classmethod
    def from_omm(cls, ts: Timescale, elements: Mapping[str, object]) -> Self: ...
    def at[T: Numeric](self, t: Time[T]) -> Geocentric[T]: ...
    def find_events(
        self,
        topos: GeographicPosition[float],
        t0: Time[float],
        t1: Time[float],
        altitude_degrees: float = 0.0,
    ) -> tuple[Time[NDArray[np.float64]], NDArray[np.int16]]: ...
