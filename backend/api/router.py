from fastapi import APIRouter
from backend.api.chat import router as chat_router
from backend.api.models import router as models_router
from backend.api.schools import router as schools_router
from backend.api.tools import router as tools_router
from backend.api.mcp import router as mcp_router
from backend.api.teams import router as teams_router
from backend.api.task_pro import router as task_pro_router

api_router = APIRouter()

api_router.include_router(chat_router, prefix="/chat", tags=["chat"])
api_router.include_router(models_router, prefix="/models", tags=["models"])
api_router.include_router(schools_router, prefix="/schools", tags=["schools"])
api_router.include_router(tools_router, prefix="/tools", tags=["tools"])
api_router.include_router(mcp_router, prefix="/mcp", tags=["mcp"])
api_router.include_router(teams_router, prefix="/teams", tags=["teams"])
api_router.include_router(task_pro_router, prefix="/task-pro", tags=["task-pro"])


@api_router.get("/health")
async def health_check():
    return {"status": "ok", "message": "AgentHome API is running"}
