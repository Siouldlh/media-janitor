"""Exécuteur sécurisé du plan de suppression."""
from typing import List, Dict, Any
from datetime import datetime

from app.db.models import Plan, PlanItem, Run, RunItem
from app.db.database import get_db_sync
from app.services.radarr import RadarrService
from app.services.sonarr import SonarrService
from app.services.qbittorrent import QBittorrentService
from app.services.plex import PlexService
from app.config import get_config


class Executor:
    """Exécute un plan de suppression de manière sécurisée."""

    def __init__(self):
        self.config = get_config()
        self.radarr_service = RadarrService() if self.config.radarr else None
        self.sonarr_service = SonarrService() if self.config.sonarr else None
        self.qb_service = QBittorrentService() if self.config.qbittorrent else None
        self.plex_service = PlexService() if self.config.plex else None

    async def execute_plan(self, plan_id: int) -> int:
        """Exécute un plan (uniquement les items selected=true)."""
        db = get_db_sync()

        # Récupérer le plan
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise ValueError(f"Plan {plan_id} not found")

        # Récupérer les items sélectionnés
        plan_items = db.query(PlanItem).filter(
            PlanItem.plan_id == plan_id,
            PlanItem.selected == True
        ).all()

        if not plan_items:
            raise ValueError("No selected items to execute")

        # Créer Run
        run = Run(
            plan_id=plan_id,
            status="RUNNING",
            results_json={"success_count": 0, "failed_count": 0, "errors": []}
        )
        db.add(run)
        db.commit()
        db.refresh(run)

        success_count = 0
        failed_count = 0
        errors = []

        # Exécuter chaque item
        for plan_item in plan_items:
            try:
                await self._execute_item(plan_item, run, db)
                success_count += 1
            except Exception as e:
                failed_count += 1
                error_msg = f"Item {plan_item.id} ({plan_item.title}): {str(e)}"
                errors.append(error_msg)

                # Créer RunItem avec erreur
                run_item = RunItem(
                    run_id=run.id,
                    plan_item_id=plan_item.id,
                    status="FAILED",
                    error=error_msg,
                )
                db.add(run_item)

        # Mettre à jour le Run
        run.finished_at = datetime.utcnow()
        run.status = "COMPLETED" if failed_count == 0 else "FAILED"
        run.results_json = {
            "success_count": success_count,
            "failed_count": failed_count,
            "errors": errors
        }
        db.commit()

        # Mettre à jour le Plan
        plan.status = "APPLIED"
        db.commit()

        return run.id

    async def _execute_item(self, plan_item: PlanItem, run: Run, db) -> None:
        """Exécute un PlanItem selon l'ordre sécurisé."""
        run_item = RunItem(
            run_id=run.id,
            plan_item_id=plan_item.id,
            status="RUNNING",
        )
        db.add(run_item)
        db.commit()

        try:
            # 1. qBittorrent : Supprimer tous les torrents liés (cross-seed)
            # IMPORTANT: Toujours deleteFiles=false pour qBittorrent
            # Les fichiers seront supprimés par Radarr/Sonarr ensuite
            qb_hashes = plan_item.qb_hashes_json or []
            if qb_hashes and self.qb_service:
                try:
                    # Toujours deleteFiles=false pour qBittorrent (sécurité)
                    await self.qb_service.delete_torrents(qb_hashes, delete_files=False)
                    run_item.qb_removed = True
                    run_item.qb_removed_at = datetime.utcnow()
                    db.commit()
                except Exception as e:
                    # Si qB échoue, on ne continue PAS (rollback logique)
                    raise Exception(f"qBittorrent deletion failed: {str(e)}")

            # 2. Radarr/Sonarr : Supprimer via API
            if plan_item.media_type == "movie" and self.radarr_service:
                radarr_id = plan_item.meta_json.get("radarr_id")
                if radarr_id:
                    try:
                        await self.radarr_service.delete_movie(radarr_id, delete_files=True)
                        run_item.radarr_sonarr_removed = True
                        run_item.radarr_sonarr_removed_at = datetime.utcnow()
                        db.commit()
                    except Exception as e:
                        raise Exception(f"Radarr deletion failed: {str(e)}")

            elif plan_item.media_type in ["series", "episode"] and self.sonarr_service:
                sonarr_id = plan_item.meta_json.get("sonarr_id")
                if sonarr_id:
                    try:
                        await self.sonarr_service.delete_series(sonarr_id, delete_files=True)
                        run_item.radarr_sonarr_removed = True
                        run_item.radarr_sonarr_removed_at = datetime.utcnow()
                        db.commit()
                    except Exception as e:
                        raise Exception(f"Sonarr deletion failed: {str(e)}")

            # 3. Plex : Refresh/empty trash (optionnel)
            if self.plex_service and self.config.plex:
                try:
                    # Refresh library (optionnel, peut être configuré)
                    # self.plex_service.refresh_library()
                    # self.plex_service.empty_trash()
                    run_item.plex_refreshed = True
                    run_item.plex_refreshed_at = datetime.utcnow()
                    db.commit()
                except Exception as e:
                    # Plex refresh n'est pas critique, on continue
                    pass

            # Succès
            run_item.status = "SUCCESS"
            db.commit()

        except Exception as e:
            run_item.status = "FAILED"
            run_item.error = str(e)
            db.commit()
            raise

