"""Shared types for orbital elements, cached data and JSON responses."""

from typing import Literal, NotRequired, TypedDict

type Group = Literal[
    "stations",
    "visual",
    "active",
    "last-30-days",
    "analyst",
    "weather",
    "resource",
    "sar",
    "sarsat",
    "dmc",
    "tdrss",
    "argos",
    "planet",
    "spire",
    "starlink",
    "oneweb",
    "kuiper",
    "qianfan",
    "hulianwang",
    "geo",
    "intelsat",
    "ses",
    "eutelsat",
    "telesat",
    "iridium-NEXT",
    "orbcomm",
    "globalstar",
    "amateur",
    "satnogs",
    "x-comm",
    "other-comm",
    "gnss",
    "gps-ops",
    "glo-ops",
    "galileo",
    "beidou",
    "sbas",
    "science",
    "geodetic",
    "engineering",
    "education",
    "cubesat",
    "military",
    "radar",
    "fengyun-1c-debris",
    "iridium-33-debris",
    "cosmos-2251-debris",
]
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
    id: Group
    name: str
    category: str


class ObserverData(TypedDict):
    name: str
    latitude_deg: float
    longitude_deg: float
    elevation_m: float


class StatusResponse(TypedDict):
    status: str
    utc: str
    source: str
    propagator: str
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
    range_km: float


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
