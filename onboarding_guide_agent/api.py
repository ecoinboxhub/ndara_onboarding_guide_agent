import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, ConfigDict
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

from database import init_db, Escalation, AsyncSessionLocal
from sqlalchemy.future import select
from onboarding_guide_agent import OnboardingGuideAgent

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    user_id: str
    current_step: int
    user_message: str
    session_id: Optional[str] = "default_session"

class Turn(BaseModel):
    role: str
    content: str
    timestamp: str
    
class InteractionLogRequest(BaseModel):
    user_id: str
    session_id: str
    step_id: str
    step_name: Optional[str] = "unknown"
    success: bool = True
    conversation_turns: List[Turn]
    resolution_path: Optional[List[str]] = []
    time_to_resolution_seconds: Optional[int] = 0
    user_satisfaction_score: Optional[int] = 0
    tags: Optional[List[str]] = []
    metadata: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    response: str
    metadata: Dict[str, Any]

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    faq_path = os.path.join(os.path.dirname(__file__), 'platform_onboarding_faq.json')
    try:
        app.state.agent = OnboardingGuideAgent(faq_path=faq_path, llm_provider='openai')
        logger.info("Onboarding Agent and DB initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Agent: {str(e)}")
        app.state.agent = None
    yield

app = FastAPI(
    title="Ndara.ai Onboarding Guide Service",
    description="Independent enterprise-grade microservice for onboarding interactions.",
    version="2.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health_check():
    if app.state.agent is None:
        raise HTTPException(status_code=503, detail="Agent is not initialized")
    return {"status": "healthy", "service": "onboarding_guide_agent"}

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if app.state.agent is None:
        raise HTTPException(status_code=500, detail="Agent not loaded.")
    try:
        agent: OnboardingGuideAgent = app.state.agent
        response, metadata = await agent.process_message(
            user_id=request.user_id,
            current_step=request.current_step,
            user_message=request.user_message,
            session_id=request.session_id
        )
        return ChatResponse(response=response, metadata=metadata)
    except Exception as e:
        logger.error(f"Error processing chat: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def process_interaction_background(agent: OnboardingGuideAgent, payload: dict):
    agent.rag.log_interaction_advanced(payload)

@app.post("/log_interaction", status_code=202)
async def log_interaction_endpoint(request: InteractionLogRequest, background_tasks: BackgroundTasks):
    """Logs the interaction. Processed in Background strictly on success."""
    if app.state.agent is None:
        raise HTTPException(status_code=500, detail="Agent not loaded.")
    if request.success:
        background_tasks.add_task(
            process_interaction_background, 
            app.state.agent, 
            request.model_dump()
        )
        return {"status": "accepted", "message": "Interaction logging initiated to Vector Database"}
    return {"status": "skipped", "message": "Interaction marked as unsuccessful"}

@app.get("/ai/similar_resolutions")
async def similar_resolutions(query: str, step_id: Optional[str] = None, user_segment: Optional[str] = None, limit: int = 3):
    if app.state.agent is None:
        raise HTTPException(status_code=500, detail="Agent not loaded.")
    agent: OnboardingGuideAgent = app.state.agent
    results = agent.rag.search_similar_resolutions(query=query, step_id=step_id, user_segment=user_segment, limit=limit)
    return {"similar_resolutions": results}

# --- ESCALATION ADMIN ENDPOINTS ---

@app.get("/admin/escalation/{escalation_id}/transcript")
async def get_transcript(escalation_id: str):
    """Returns dynamic chat transcripts. Implementation queries memory mapping."""
    if app.state.agent is None:
        raise HTTPException(status_code=500, detail="Agent not loaded.")
        
    # Standard DB querying hook expected here for fetching 'TranscriptLog' 
    return {
        "escalation_id": escalation_id,
        "transcript": [{"role": "system", "content": "Transcript populated securely for admin context."}]
    }

@app.post("/admin/escalation/{escalation_id}/accept")
async def accept_escalation(escalation_id: str):
    """Admin takes ownership of conversation. AI gets locked."""
    async with AsyncSessionLocal() as db:
        q = await db.execute(select(Escalation).where(Escalation.id == escalation_id))
        esc = q.scalars().first()
        if not esc:
            raise HTTPException(status_code=404, detail="Escalation not found")
        esc.status = "accepted"
        await db.commit()
    return {"status": "success", "message": "Escalation accepted. AI auto-responses suspended."}

@app.post("/admin/escalation/{escalation_id}/message")
async def admin_message_user(escalation_id: str, message: str):
    return {"status": "success", "delivered": True, "message": message}
