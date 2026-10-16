from uuid import uuid4
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/sso", tags=["Epic 8 - SSO ENT (simulation)"])

class DemoLoginRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr

@router.post("/demo-login")
def demo_login(request: DemoLoginRequest):
    # Prototype UI only: this does NOT authenticate against the real ENT.
    return {"mode": "demo", "user": {"id": str(uuid4()), "name": request.name.strip(), "email": str(request.email), "provider": "ESIC-DEMO"}, "warning": "Authentification de démonstration uniquement; ne pas utiliser comme sécurité de production."}
