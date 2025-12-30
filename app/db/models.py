"""SQLAlchemy models for database."""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Plan(Base):
    """Plan de suppression généré par un scan."""
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String, default="DRAFT", nullable=False)  # DRAFT, APPLIED, CANCELLED
    summary_json = Column(JSON, default=dict)  # {movies_count, series_count, episodes_count, total_size_bytes}

    # Relationships
    items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan")
    runs = relationship("Run", back_populates="plan")


class PlanItem(Base):
    """Item candidat à la suppression dans un plan."""
    __tablename__ = "plan_items"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    selected = Column(Boolean, default=True, nullable=False)  # Sélectionné pour suppression
    media_type = Column(String, nullable=False)  # movie, series, episode
    title = Column(String, nullable=False)
    year = Column(Integer, nullable=True)
    ids_json = Column(JSON, default=dict)  # {tmdb, tvdb, imdb}
    path = Column(String, nullable=False)
    size_bytes = Column(Integer, default=0)
    last_viewed_at = Column(DateTime, nullable=True)
    view_count = Column(Integer, default=0)
    never_watched = Column(Boolean, default=False)
    rule = Column(String, nullable=True)  # not_watched_60d, never_watched_60d, etc.
    protected_reason = Column(String, nullable=True)  # Si non candidat, raison
    qb_hashes_json = Column(JSON, default=list)  # Liste des hash torrents qBittorrent
    meta_json = Column(JSON, default=dict)  # Données additionnelles (Overseerr, tags, etc.)

    # Relationships
    plan = relationship("Plan", back_populates="items")
    run_items = relationship("RunItem", back_populates="plan_item")


class Run(Base):
    """Exécution d'un plan (apply)."""
    __tablename__ = "runs"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)
    status = Column(String, default="RUNNING", nullable=False)  # RUNNING, COMPLETED, FAILED, CANCELLED
    results_json = Column(JSON, default=dict)  # {success_count, failed_count, errors}

    # Relationships
    plan = relationship("Plan", back_populates="runs")
    items = relationship("RunItem", back_populates="run")


class RunItem(Base):
    """Résultat d'exécution pour un PlanItem."""
    __tablename__ = "run_items"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(Integer, ForeignKey("runs.id"), nullable=False, index=True)
    plan_item_id = Column(Integer, ForeignKey("plan_items.id"), nullable=False, index=True)
    status = Column(String, nullable=False)  # SUCCESS, FAILED, SKIPPED
    error = Column(Text, nullable=True)
    qb_removed = Column(Boolean, default=False)
    qb_removed_at = Column(DateTime, nullable=True)
    radarr_sonarr_removed = Column(Boolean, default=False)
    radarr_sonarr_removed_at = Column(DateTime, nullable=True)
    plex_refreshed = Column(Boolean, default=False)
    plex_refreshed_at = Column(DateTime, nullable=True)

    # Relationships
    run = relationship("Run", back_populates="items")
    plan_item = relationship("PlanItem", back_populates="run_items")


class Protection(Base):
    """Exclusions persistées (items protégés manuellement)."""
    __tablename__ = "protections"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    media_type = Column(String, nullable=False)  # movie, series
    tmdb_id = Column(Integer, nullable=True)
    tvdb_id = Column(Integer, nullable=True)
    imdb_id = Column(String, nullable=True)
    path = Column(String, nullable=True)
    reason = Column(String, nullable=True)  # Raison de la protection

