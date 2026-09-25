from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uuid

from backend.guard import inspect_tool_call
from backend.models import ToolCall  # Ensure policy_engine has evaluate_policy()

app = FastAPI(title="AgentGuard Security Gateway")

# Enable CORS for Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for security events
security_events = []

class EvaluationRequest(BaseModel):
    agent_id: str = "demo-agent"
    tool: str
    prompt: str = ""

class ActionDecisionRequest(BaseModel):
    event_id: str
    action: str  # "APPROVE" or "DENY"

@app.get("/")
def read_root():
    return {"name": "AgentGuard", "status": "running", "version": "0.1.0"}

@app.get("/events")
def get_events():
    """Returns all recorded security audit events."""
    return security_events

@app.post("/evaluate")
def evaluate_event(request: EvaluationRequest):
    tool_call = ToolCall(
        agent_id=request.agent_id,
        tool=request.tool,
        arguments={
            "prompt": request.prompt
        }
    )

    inspection_result = inspect_tool_call(tool_call)

    event_id = str(uuid.uuid4())[:8]

    event = {
        "id": event_id,
        "timestamp": datetime.now().isoformat(),
        "agent_id": inspection_result["agent_id"],
        "tool": inspection_result["tool"],
        "prompt": request.prompt,
        "risk": inspection_result["risk"],
        "decision": inspection_result["decision"],
        "reason": inspection_result["reason"],
    }

    security_events.insert(0, event)

    return event

@app.post("/action")
def update_action(request: ActionDecisionRequest):
    """Endpoint for Human-in-the-Loop decision (Approve / Deny)."""
    for event in security_events:
        if event["id"] == request.event_id:
            if request.action == "APPROVE":
                event["decision"] = "APPROVED_BY_ADMIN"
                event["reason"] = "Manually approved by Security Administrator on Dashboard."
            elif request.action == "DENY":
                event["decision"] = "DENIED_BY_ADMIN"
                event["reason"] = "Manually rejected by Security Administrator on Dashboard."
            return {"status": "success", "event": event}
            
    raise HTTPException(status_code=404, detail="Event ID not found")