"""Configuration management with YAML and environment variables."""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class PlexConfig(BaseModel):
    url: str
    token: str
    libraries: dict[str, str] = Field(default_factory=lambda: {"movies": "Films", "series": "Series"})


class RadarrConfig(BaseModel):
    url: str
    api_key: str
    delete_method: str = "api"  # api|filesystem
    protected_tags: List[str] = Field(default_factory=list)


class SonarrConfig(BaseModel):
    url: str
    api_key: str
    protected_tags: List[str] = Field(default_factory=list)


class OverseerrConfig(BaseModel):
    url: str
    api_key: str
    protect_if_request_active: bool = True
    protect_if_request_younger_than_days: int = 30
    requested_by_must_have_watched: bool = False


class QBittorrentConfig(BaseModel):
    url: str
    username: str
    password: str
    protect_categories: List[str] = Field(default_factory=list)
    remove_torrent_first: bool = True
    delete_data_with_qb: bool = False
    match_mode: str = "path"  # path|files


class TautulliConfig(BaseModel):
    url: str
    api_key: str


class RulesConfig(BaseModel):
    movies: dict = Field(default_factory=lambda: {
        "delete_if_not_watched_days": 60,
        "if_never_watched_use_added_days": 60
    })
    series: dict = Field(default_factory=lambda: {
        "delete_episodes_not_watched_days": 60,
        "keep_last_n_episodes": 0,
        "delete_entire_series_if_inactive_days": 120
    })


class SchedulerConfig(BaseModel):
    enabled: bool = True
    cadence: str = "1 day"
    timezone: str = "Europe/Paris"


class AppConfig(BaseModel):
    dry_run_default: bool = True
    require_manual_approval: bool = True
    require_confirm_phrase: Optional[str] = None  # Ex: "DELETE" à taper pour confirmer
    excluded_paths: List[str] = Field(default_factory=list)  # Chemins à exclure
    max_items_per_scan: Optional[int] = None  # Limite le nombre d'items par scan
    data_dir: str = "/data"
    log_level: str = "INFO"


class Config(BaseSettings):
    plex: Optional[PlexConfig] = None
    tautulli: Optional[TautulliConfig] = None
    radarr: Optional[RadarrConfig] = None
    sonarr: Optional[SonarrConfig] = None
    overseerr: Optional[OverseerrConfig] = None
    qbittorrent: Optional[QBittorrentConfig] = None
    rules: RulesConfig = Field(default_factory=RulesConfig)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    app: AppConfig = Field(default_factory=AppConfig)

    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"

    @classmethod
    def load_from_yaml(cls, yaml_path: str) -> "Config":
        """Load configuration from YAML file, override with env vars."""
        config_path = Path(yaml_path)
        if not config_path.exists():
            raise FileNotFoundError(
                f"Config file not found: {yaml_path}\n"
                f"Please create config/config.yaml from config.example.yaml\n"
                f"Make sure the volume is mounted: -v ./config:/config:ro"
            )

        with open(config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

        # Override with environment variables
        env_overrides = {}
        for key in ["plex", "tautulli", "radarr", "sonarr", "overseerr", "qbittorrent"]:
            if key in yaml_data:
                for subkey, value in yaml_data[key].items():
                    env_key = f"{key.upper()}__{subkey.upper()}"
                    env_value = os.getenv(env_key)
                    if env_value:
                        if key not in env_overrides:
                            env_overrides[key] = {}
                        env_overrides[key][subkey] = env_value

        # Merge env overrides
        for key, value in env_overrides.items():
            if key in yaml_data:
                yaml_data[key].update(value)

        return cls(**yaml_data)


# Global config instance (will be initialized in main.py)
config: Optional[Config] = None


def get_config() -> Config:
    """Get the global config instance."""
    if config is None:
        raise RuntimeError("Config not initialized. Call init_config() first.")
    return config


def init_config(config_path: str = "/config/config.yaml") -> Config:
    """Initialize global config from YAML file."""
    global config
    config = Config.load_from_yaml(config_path)
    return config

