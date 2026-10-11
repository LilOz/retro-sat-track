from collections.abc import Iterable
from datetime import datetime
from typing import overload

import numpy as np
from numpy.typing import NDArray

from ._typing import FloatArray, Numeric

class Time[T: Numeric = Numeric]:
    @overload
    def utc_datetime(self: Time[float]) -> datetime: ...
    @overload
    def utc_datetime(self: Time[FloatArray]) -> NDArray[np.object_]: ...
    def __len__(self) -> int: ...
    def __getitem__(self, index: int) -> Time[float]: ...

class Timescale:
    def from_datetime(self, dt: datetime) -> Time[float]: ...
    def from_datetimes(self, dates: Iterable[datetime]) -> Time[FloatArray]: ...
