from pydantic import BaseModel, ConfigDict, Field


class Observer(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    name: str = Field(default="Home station", min_length=1, max_length=64)
    latitude_deg: float = Field(ge=-90, le=90)
    longitude_deg: float = Field(ge=-180, le=180)
    elevation_m: float = Field(default=0, ge=-500, le=9000)
