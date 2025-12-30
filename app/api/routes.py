"""API routes."""
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List
import logging
import traceback

from app.db.database import get_db
from app.db.models import Plan, PlanItem, Run, RunItem, Protection
from app.api.models import (
    ScanResponse, PlanResponse, PlanItemResponse, UpdateItemsRequest,
    ApplyRequest, ApplyResponse, RunResponse, ProtectRequest, DiagnosticsResponse
)
from app.core.planner import Planner
from app.core.executor import Executor
from app.core.safety import SafetyChecker
from app.services.plex import PlexService
from app.services.radarr import RadarrService
from app.services.sonarr import SonarrService
from app.services.overseerr import OverseerrService
from app.services.qbittorrent import QBittorrentService
from app.config import get_config

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/scan", response_model=ScanResponse)
async def scan():
    """Lance un scan et génère un plan."""
    logger.info("=== Starting scan ===")
    try:
        planner = Planner()
        plan_id = await planner.generate_plan()
        logger.info(f"Scan completed successfully, plan_id: {plan_id}")

        db = next(get_db())
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        stats = plan.summary_json if plan else {}

        return ScanResponse(plan_id=plan_id, stats=stats)
    except Exception as e:
        # Log la stacktrace complète
        logger.exception("Scan failed with exception")
        
        # Préparer la réponse d'erreur détaillée
        error_detail = {
            "error": str(e),
            "type": e.__class__.__name__,
            "message": f"Scan failed: {str(e)}",
            "traceback": traceback.format_exc()
        }
        
        # Retourner une réponse JSON avec la stacktrace
        return JSONResponse(
            status_code=500,
            content=error_detail
        )


@router.get("/api/plan/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: int, db: Session = Depends(get_db)):
    """Récupère un plan avec ses items."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan_items = db.query(PlanItem).filter(PlanItem.plan_id == plan_id).all()

    items = []
    for item in plan_items:
        items.append(PlanItemResponse(
            id=item.id,
            selected=item.selected,
            media_type=item.media_type,
            title=item.title,
            year=item.year,
            ids=item.ids_json or {},
            path=item.path,
            size_bytes=item.size_bytes,
            last_viewed_at=item.last_viewed_at,
            view_count=item.view_count,
            never_watched=item.never_watched,
            rule=item.rule,
            protected_reason=item.protected_reason,
            qb_hashes=item.qb_hashes_json or [],
            meta=item.meta_json or {},
        ))

    return PlanResponse(
        id=plan.id,
        created_at=plan.created_at,
        status=plan.status,
        summary=plan.summary_json or {},
        items=items,
    )


@router.patch("/api/plan/{plan_id}/items")
async def update_items(plan_id: int, request: UpdateItemsRequest, db: Session = Depends(get_db)):
    """Met à jour la sélection des items."""
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if request.select_all is not None:
        # Toggle all
        db.query(PlanItem).filter(PlanItem.plan_id == plan_id).update(
            {"selected": request.select_all}
        )
    else:
        # Update specific items
        for item_update in request.items:
            item_id = item_update.get("id")
            selected = item_update.get("selected")
            if item_id is not None and selected is not None:
                db.query(PlanItem).filter(
                    PlanItem.id == item_id,
                    PlanItem.plan_id == plan_id
                ).update({"selected": selected})

    db.commit()
    return {"message": "Items updated"}


@router.post("/api/plan/{plan_id}/apply", response_model=ApplyResponse)
async def apply_plan(plan_id: int, request: ApplyRequest):
    """Exécute un plan (uniquement items selected=true)."""
    from app.config import get_config
    config = get_config()
    
    # Vérifier la phrase de confirmation si requise
    if config.app.require_confirm_phrase:
        if not request.confirm_phrase or request.confirm_phrase != config.app.require_confirm_phrase:
            raise HTTPException(
                status_code=400,
                detail=f"Confirmation phrase required. Expected: {config.app.require_confirm_phrase}"
            )
    
    try:
        executor = Executor()
        run_id = await executor.execute_plan(plan_id)
        return ApplyResponse(run_id=run_id, message="Plan execution started")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(run_id: int, db: Session = Depends(get_db)):
    """Récupère le statut d'une exécution."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunResponse(
        id=run.id,
        plan_id=run.plan_id,
        started_at=run.started_at,
        finished_at=run.finished_at,
        status=run.status,
        results=run.results_json or {},
    )


@router.get("/api/runs/{run_id}/logs")
async def get_run_logs(run_id: int, db: Session = Depends(get_db)):
    """Récupère les logs d'une exécution."""
    run = db.query(Run).filter(Run.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    run_items = db.query(RunItem).filter(RunItem.run_id == run_id).all()

    logs = []
    for item in run_items:
        plan_item = db.query(PlanItem).filter(PlanItem.id == item.plan_item_id).first()
        logs.append({
            "plan_item_id": item.plan_item_id,
            "title": plan_item.title if plan_item else "Unknown",
            "status": item.status,
            "error": item.error,
            "qb_removed": item.qb_removed,
            "radarr_sonarr_removed": item.radarr_sonarr_removed,
            "plex_refreshed": item.plex_refreshed,
        })

    return {"logs": logs}


@router.post("/api/protect")
async def protect_item(request: ProtectRequest, db: Session = Depends(get_db)):
    """Crée une protection (exclusion) pour un média."""
    protection = Protection(
        media_type=request.media_type,
        tmdb_id=request.tmdb_id,
        tvdb_id=request.tvdb_id,
        imdb_id=request.imdb_id,
        path=request.path,
        reason=request.reason,
    )
    db.add(protection)
    db.commit()
    return {"message": "Item protected"}


@router.get("/api/diagnostics", response_model=DiagnosticsResponse)
async def diagnostics():
    """Vérifie les connexions aux APIs."""
    config = get_config()
    results = {
        "plex": {"connected": False, "error": None},
        "radarr": {"connected": False, "error": None},
        "sonarr": {"connected": False, "error": None},
        "overseerr": {"connected": False, "error": None},
        "qbittorrent": {"connected": False, "error": None},
    }

    # Test Plex
    if config.plex:
        try:
            service = PlexService()
            service._get_server()
            results["plex"]["connected"] = True
        except Exception as e:
            results["plex"]["error"] = str(e)

    # Test Radarr
    if config.radarr:
        try:
            service = RadarrService()
            service.get_movies_sync()
            results["radarr"]["connected"] = True
        except Exception as e:
            results["radarr"]["error"] = str(e)

    # Test Sonarr
    if config.sonarr:
        try:
            service = SonarrService()
            service.get_series_sync()
            results["sonarr"]["connected"] = True
        except Exception as e:
            results["sonarr"]["error"] = str(e)

    # Test Overseerr
    if config.overseerr:
        try:
            service = OverseerrService()
            service.get_requests_sync()
            results["overseerr"]["connected"] = True
        except Exception as e:
            results["overseerr"]["error"] = str(e)

    # Test qBittorrent
    if config.qbittorrent:
        try:
            service = QBittorrentService()
            service.get_torrents()
            results["qbittorrent"]["connected"] = True
        except Exception as e:
            results["qbittorrent"]["error"] = str(e)

    return DiagnosticsResponse(**results)


@router.get("/api/config")
async def get_config_endpoint():
    """Récupère la configuration actuelle (sans secrets)."""
    config = get_config()
    return {
        "plex": {"url": config.plex.url if config.plex else None},
        "radarr": {"url": config.radarr.url if config.radarr else None},
        "sonarr": {"url": config.sonarr.url if config.sonarr else None},
        "overseerr": {"url": config.overseerr.url if config.overseerr else None},
        "qbittorrent": {"url": config.qbittorrent.url if config.qbittorrent else None},
        "rules": config.rules.dict() if config.rules else {},
        "scheduler": config.scheduler.dict() if config.scheduler else {},
        "app": config.app.dict() if config.app else {},
    }

