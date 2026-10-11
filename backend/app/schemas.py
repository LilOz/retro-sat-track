"""Shared types for orbital elements, cached data and JSON responses."""

from typing import Literal, NotRequired, TypedDict

type Group = Literal["stations", "starlink", "science", "gps-ops"]
type OrbitalNumber = float | str


class OrbitalElements(TypedDict):
    NORAD_CAT_ID: int | str
    OBJECT_NAME: str
    EPOCH: str
    MEAN_MOTION: OrbitalNumber
    ECCENTRICITY: OrbitalNumber
    INCLINATION: OrbitalNumber
    RA_OF_ASC_NODE: OrbitalNumber
    ARG_OF_PERICENTER: OrbitalNumber
    MEAN_ANOMALY: OrbitalNumber
    BSTAR: OrbitalNumber
    MEAN_MOTION_DOT: OrbitalNumber
    MEAN_MOTION_DDOT: OrbitalNumber


class CatalogSnapshot(TypedDict):
    fetched_at: float
    records: list[OrbitalElements]


class CatalogAttempt(TypedDict):
    retry_after: float
    error: NotRequired[str]


class CatalogFreshness(TypedDict):
    loaded: bool
    error: str | None
    count: NotRequired[int]
    fetched_at: NotRequired[str]
    download_age_seconds: NotRequired[int]
    stale: NotRequired[bool]


class GroupFreshness(CatalogFreshness):
    id: str
    name: str


class ObserverData(TypedDict):
    name: str
    latitude_deg: float
    longitude_deg: float
    elevation_m: float


class StatusResponse(TypedDict):
    status: str
    utc: str
    source: str
    provider_configured: bool
    provider_error: str | None
    observer: ObserverData | None
    groups: list[GroupFreshness]


class SatelliteSummary(TypedDict):
    id: int
    name: str
    epoch: str
    inclination_deg: OrbitalNumber


class SatelliteList(TypedDict):
    group: Group
    total: int
    offset: int
    catalog: CatalogFreshness
    satellites: list[SatelliteSummary]


class SatelliteState(TypedDict):
    id: int
    name: str
    utc: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
    velocity_km_s: float
    inclination_deg: float
    period_minutes: float
    eccentricity: float
    mean_orbital_phase_deg: float
    element_epoch: str
    element_age_hours: float
    elements_stale: bool
    azimuth_deg: float
    elevation_deg: float
    range_km: float
    above_horizon: bool
    position_ecef_km: list[float]


class GroundTrackPoint(TypedDict):
    utc: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float


class OrbitTrack(TypedDict):
    id: int
    utc: str
    period_seconds: float
    orbit_ecef_km: list[list[float]]
    ground_track: list[GroundTrackPoint]


class SceneResponse(TypedDict):
    utc: str
    states: list[SatelliteState]
    catalog: CatalogFreshness
    observer_configured: bool


class SkyPathPoint(TypedDict):
    azimuth_deg: float
    elevation_deg: float
    range_km: float | None


class SatellitePass(TypedDict):
    id: str
    satellite_id: int
    name: str
    rise_utc: str
    culmination_utc: str
    set_utc: str
    max_elevation_deg: float
    rise_azimuth_deg: float
    set_azimuth_deg: float
    rise_direction: str
    set_direction: str
    duration_seconds: int
    in_progress: bool
    min_elevation_deg: float
    visibility: str
    sky_path: list[SkyPathPoint]


class PassForecast(TypedDict):
    satellite_id: int
    observer: ObserverData
    generated_utc: str
    window_end_utc: str
    min_elevation_deg: float
    passes: list[SatellitePass]
    above_mask_now: bool
    note: str


class ProviderState(TypedDict):
    id: int
    name: str
    utc: str
    latitude_deg: float
    longitude_deg: float
    altitude_km: float
    velocity_km_s: float | None
    inclination_deg: float
    period_minutes: float
    eccentricity: float
    mean_orbital_phase_deg: float | None
    element_epoch: str
    element_age_hours: float
    elements_stale: bool
    azimuth_deg: float
    elevation_deg: float
    range_km: float | None
    above_horizon: bool
    position_globe_km: list[float]
    source: str


class ProviderTrack(TypedDict):
    id: int
    utc: str
    window_seconds: int
    path_globe_km: list[list[float]]
    ground_track: list[GroundTrackPoint]
    source: str


class ProviderScene(TypedDict):
    utc: str
    states: list[ProviderState]
    catalog: CatalogFreshness
    observer_configured: bool


class ProviderForecast(TypedDict):
    satellite_id: int
    observer: ObserverData
    generated_utc: str
    window_end_utc: str
    min_peak_elevation_deg: float
    passes: list[SatellitePass]
    note: str
