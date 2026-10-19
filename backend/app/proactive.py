from datetime import date
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/proactive", tags=["Epic 8 - informations contextuelles"])

# Jeu de démonstration : remplacer/compléter ces informations avec le calendrier officiel ESIC.
# Les dates ne sont volontairement pas présentées comme des dates officielles.
DEMO_ITEMS = [
    {"id": "welcome", "title_fr": "Préparer la rentrée", "body_fr": "Consultez l'ENT et les annonces de scolarité pour vérifier les salles, horaires et documents à apporter.", "title_en": "Get ready for the new term", "body_en": "Check the student portal and official announcements for rooms, schedules and required documents.", "months": [8, 9, 1]},
    {"id": "exams", "title_fr": "Période de révisions", "body_fr": "Pensez à vérifier votre calendrier d'examens officiel et à anticiper les révisions.", "title_en": "Revision period", "body_en": "Check your official exam timetable and plan your revision sessions ahead of time.", "months": [1, 5, 6]},
    {"id": "student-services", "title_fr": "Besoin d'aide ?", "body_fr": "Pour une information fiable, contactez le service concerné via les coordonnées officielles de l'établissement.", "title_en": "Need help?", "body_en": "For reliable information, contact the relevant service using the institution's official contact details.", "months": list(range(1, 13))},
]

@router.get("/info")
def proactive_info(language: str = Query("fr", pattern="^(fr|en)$")):
    month = date.today().month
    items = []
    for item in DEMO_ITEMS:
        if month in item["months"]:
            items.append({"id": item["id"], "title": item["title_en"] if language == "en" else item["title_fr"], "body": item["body_en"] if language == "en" else item["body_fr"], "date": ""})
    return {"items": items, "mode": "demo", "note": "Messages de démonstration à valider avec le calendrier officiel ESIC."}
