from ._typing import Numeric

class Angle[T: Numeric = Numeric]:
    @property
    def degrees(self) -> T: ...

class Distance[T: Numeric = Numeric]:
    @property
    def km(self) -> T: ...

class Velocity[T: Numeric = Numeric]:
    @property
    def km_per_s(self) -> T: ...
