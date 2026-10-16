from datetime import datetime, timezone
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/notifications", tags=["Epic 8 - notifications"])

# Notifications de démonstration. En production, stocker les annonces dans la base et
# ajouter Web Push (VAPID + abonnements) pour notifier même quand l'application est fermée.
NOTIFICATIONS = [
    {"id": "demo-001", "title_fr": "Bienvenue sur ESIC Assistant", "body_fr": "Les informations importantes du campus apparaîtront ici.", "title_en": "Welcome to ESIC Assistant", "body_en": "Important campus updates will appear here.", "active": True},
]

@router.get("")
def list_notifications(language: str = Query("fr", pattern="^(fr|en)$")):
    items = []
    for n in NOTIFICATIONS:
        if not n.get("active", True):
            continue
        items.append({"id": n["id"], "title": n["title_en"] if language == "en" else n["title_fr"], "body": n["body_en"] if language == "en" else n["body_fr"], "created_at": datetime.now(timezone.utc).isoformat()})
    return {"items": items, "mode": "demo-polling"}
