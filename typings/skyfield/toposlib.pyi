from ._typing import Numeric
from .positionlib import ICRF
from .units import Angle, Distance
from .vectorlib import VectorFunction

class GeographicPosition[T: Numeric = Numeric](VectorFunction):
    @property
    def latitude(self) -> Angle[T]: ...
    @property
    def longitude(self) -> Angle[T]: ...
    @property
    def elevation(self) -> Distance[T]: ...

class Geoid:
    def latlon(
        self,
        latitude_degrees: float,
        longitude_degrees: float,
        elevation_m: float = 0.0,
    ) -> GeographicPosition[float]: ...
    def geographic_position_of[T: Numeric](
        self, position: ICRF[T]
    ) -> GeographicPosition[T]: ...

wgs84: Geoid
