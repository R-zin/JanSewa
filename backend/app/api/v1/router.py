from fastapi import APIRouter
from app.api.v1.endpoints import agent, documents, automation, dashboard, digilocker, auth, metrics, speech, ocr  # workflows temporarily disabled

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(digilocker.router, prefix="/digilocker", tags=["digilocker"])
# api_router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])  # Temporarily disabled
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])  # Re-enabled with AWS Textract support
api_router.include_router(speech.router, prefix="/speech", tags=["speech"])

@api_router.get("/")
async def root():
    return {"message": "Government Services Assistant API v1"}
