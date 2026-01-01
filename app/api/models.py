"""Pydantic models for API requests/responses."""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class ScanResponse(BaseModel):
    plan_id: Optional[int] = None
    scan_id: Optional[str] = None
    stats: Dict[str, Any]


class PlanItemResponse(BaseModel):
    id: int
    selected: bool
    media_type: str
    title: str
    year: Optional[int]
    ids: Dict[str, Any]
    path: str
    size_bytes: int
    last_viewed_at: Optional[datetime]
    view_count: int
    never_watched: bool
    rule: Optional[str]
    protected_reason: Optional[str]
    qb_hashes: List[str]
    meta: Dict[str, Any]


class PlanResponse(BaseModel):
    id: int
    created_at: datetime
    status: str
    summary: Dict[str, Any]
    items: List[PlanItemResponse]


class UpdateItemsRequest(BaseModel):
    items: List[Dict[str, Any]]  # [{id, selected}]
    select_all: Optional[bool] = None


class ApplyRequest(BaseModel):
    confirm_phrase: Optional[str] = None


class ApplyResponse(BaseModel):
    run_id: int
    message: str


class RunResponse(BaseModel):
    id: int
    plan_id: int
    started_at: datetime
    finished_at: Optional[datetime]
    status: str
    results: Dict[str, Any]


class ProtectRequest(BaseModel):
    media_type: str
    tmdb_id: Optional[int] = None
    tvdb_id: Optional[int] = None
    imdb_id: Optional[str] = None
    path: Optional[str] = None
    reason: Optional[str] = None


class DiagnosticsResponse(BaseModel):
    tautulli: Dict[str, Any]
    radarr: Dict[str, Any]
    sonarr: Dict[str, Any]
    overseerr: Dict[str, Any]
    qbittorrent: Dict[str, Any]

