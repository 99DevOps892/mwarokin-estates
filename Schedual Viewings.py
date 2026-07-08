"""
AgenticPythonSystem.py
A single-file, modern, agentic Python system (FastAPI) that provides:
- REST API for properties, schedules, notifications
- SQLite DB via SQLModel
- WebSocket manager for real-time updates to the front-end
- An AgentManager that runs lightweight "agents" asynchronously to perform tasks
- Example agents: PropertyAgent, SchedulerAgent, NotifierAgent
- Dockerfile + requirements + README embedded at the bottom

Run: `uvicorn AgenticPythonSystem:app --reload --port 8000`
"""

from typing import List, Optional, Dict, Any
import asyncio
import uuid
import datetime
from enum import Enum

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, create_engine, Session, select
import uvicorn

# ----------------------------
# Database models (SQLModel)
# ----------------------------

class Status(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    INACTIVE = "inactive"

class Property(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    location: str
    price: str
    type: str
    beds: int
    baths: int
    area: str
    status: Status = Status.ACTIVE
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())

class ScheduleItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    time: datetime.datetime
    property_id: Optional[int] = None
    status: Status = Status.PENDING
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.utcnow())
    read: bool = False

# ----------------------------
# DB setup
# ----------------------------

SQLITE_URL = "sqlite:///./agentic_system.db"
engine = create_engine(SQLITE_URL, echo=False)

def init_db():
    SQLModel.metadata.create_all(engine)

# ----------------------------
# WebSocket manager for real-time updates
# ----------------------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None):
        await websocket.accept()
        cid = client_id or str(uuid.uuid4())
        async with self.lock:
            self.active_connections[cid] = websocket
        return cid

    async def disconnect(self, client_id: str):
        async with self.lock:
            ws = self.active_connections.pop(client_id, None)
            if ws:
                await ws.close()

    async def send_json(self, data: dict, client_id: Optional[str] = None):
        """Send to single client if client_id provided, otherwise broadcast."""
        async with self.lock:
            targets = [self.active_connections[client_id]] if client_id and client_id in self.active_connections else list(self.active_connections.values())
        for ws in targets:
            try:
                await ws.send_json(data)
            except Exception:
                # ignore failing connections
                pass

manager = ConnectionManager()

# ----------------------------
# Agentic system: lightweight agents
# ----------------------------

class Agent:
    """Base agent interface - each agent should implement `handle` which is an async function."""
    name: str

    def __init__(self, name: str):
        self.name = name

    async def handle(self, task: Dict[str, Any]):
        raise NotImplementedError

class PropertyAgent(Agent):
    async def handle(self, task: Dict[str, Any]):
        # Example: auto-classify status, enrich data, or create cross-links
        action = task.get("action")
        if action == "classify":
            prop = task.get("property")
            # naive classification: mark high price > 500k as pending sale
            price_text = prop.get("price", "0").replace("$", "").replace(",", "")
            try:
                price_val = float(price_text)
            except Exception:
                price_val = 0.0
            if price_val > 500000:
                prop['status'] = Status.PENDING.value
            else:
                prop['status'] = Status.ACTIVE.value
            await asyncio.sleep(0.1)
            return {"agent": self.name, "result": prop}
        return {"agent": self.name, "result": None}

class SchedulerAgent(Agent):
    async def handle(self, task: Dict[str, Any]):
        # Example: schedule optimization
        if task.get("action") == "optimize":
            await asyncio.sleep(0.2)
            return {"agent": self.name, "result": "optimized"}
        return {"agent": self.name, "result": None}

class NotifierAgent(Agent):
    async def handle(self, task: Dict[str, Any]):
        # Example: create notification and broadcast
        msg = task.get("message")
        if msg:
            with Session(engine) as session:
                n = Notification(message=msg)
                session.add(n)
                session.commit()
                session.refresh(n)
            payload = {"type": "notification.new", "data": {
                "uuid": n.uuid,
                "message": n.message,
                "created_at": n.created_at.isoformat()
            }}
            await manager.send_json(payload)
            return {"agent": self.name, "result": n.uuid}
        return {"agent": self.name, "result": None}

# Agent manager orchestrates tasks across agents
class AgentManager:
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    def register_agent(self, agent: Agent):
        self.agents[agent.name] = agent

    async def enqueue(self, task: Dict[str, Any]):
        await self.task_queue.put(task)

    async def _worker(self):
        while True:
            task = await self.task_queue.get()
            try:
                # determine which agent(s) to run
                target = task.get("agent")
                if target:
                    agent = self.agents.get(target)
                    if agent:
                        result = await agent.handle(task)
                        # optionally broadcast completed task
                        await manager.send_json({"type": "agent.task_complete", "data": {"task": task, "result": result}})
                else:
                    # broadcast to all agents that accept the task
                    for agent in self.agents.values():
                        try:
                            result = await agent.handle(task)
                            if result:
                                await manager.send_json({"type": "agent.task_complete", "data": {"task": task, "result": result}})
                        except Exception:
                            pass
            except Exception as exc:
                print("Agent manager error:", exc)
            finally:
                self.task_queue.task_done()

    def start_background_loop(self):
        if not self._running:
            self._running = True
            asyncio.create_task(self._worker())

agent_manager = AgentManager()
agent_manager.register_agent(PropertyAgent("property-agent"))
agent_manager.register_agent(SchedulerAgent("scheduler-agent"))
agent_manager.register_agent(NotifierAgent("notifier-agent"))

# ----------------------------
# FastAPI app
# ----------------------------

app = FastAPI(title="Agentic Property Manager")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    init_db()
    agent_manager.start_background_loop()
    # create sample data if empty
    with Session(engine) as session:
        count = session.exec(select(Property)).all()
        if not count:
            p1 = Property(title="Luxury Villa in Karen", location="Karen, Nairobi", price="$450000", type="Owned", beds=5, baths=4, area="4200 sqft")
            p2 = Property(title="Modern Apartment in Westlands", location="Westlands, Nairobi", price="$3200", type="Rented", beds=3, baths=2, area="1800 sqft")
            session.add_all([p1, p2])
            session.commit()

# ----------------------------
# REST endpoints
# ----------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}

@app.get("/properties", response_model=List[Property])
def list_properties():
    with Session(engine) as session:
        props = session.exec(select(Property)).all()
        return props

@app.post("/properties", response_model=Property)
async def create_property(payload: dict, background_tasks: BackgroundTasks):
    prop = Property(
        title=payload.get("title"),
        location=payload.get("location"),
        price=payload.get("price", "$0"),
        type=payload.get("type", "Owned"),
        beds=int(payload.get("beds", 1)),
        baths=int(payload.get("baths", 1)),
        area=payload.get("area", "0 sqft")
    )
    with Session(engine) as session:
        session.add(prop)
        session.commit()
        session.refresh(prop)
    # enqueue a classification task for property-agent
    await agent_manager.enqueue({"agent": "property-agent", "action": "classify", "property": prop.dict()})
    # send a notification via notifier-agent
    await agent_manager.enqueue({"agent": "notifier-agent", "message": f"New property added: {prop.title}"})
    return prop

@app.get("/schedules", response_model=List[ScheduleItem])
def list_schedules():
    with Session(engine) as session:
        items = session.exec(select(ScheduleItem)).all()
        return items

@app.post("/schedules", response_model=ScheduleItem)
async def create_schedule(payload: dict):
    t = payload.get("time")
    try:
        dt = datetime.datetime.fromisoformat(t)
    except Exception:
        raise HTTPException(status_code=400, detail="time must be ISO format")
    item = ScheduleItem(title=payload.get("title"), time=dt, property_id=payload.get("property_id"))
    with Session(engine) as session:
        session.add(item)
        session.commit()
        session.refresh(item)
    # let scheduler-agent optimize
    await agent_manager.enqueue({"agent": "scheduler-agent", "action": "optimize", "schedule": item.dict()})
    await agent_manager.enqueue({"agent": "notifier-agent", "message": f"New schedule created: {item.title} at {item.time.isoformat()}"})
    return item

@app.get("/notifications", response_model=List[Notification])
def list_notifications():
    with Session(engine) as session:
        items = session.exec(select(Notification).order_by(Notification.created_at.desc())).all()
        return items

@app.post("/notifications/read/{notification_uuid}")
def mark_read(notification_uuid: str):
    with Session(engine) as session:
        q = session.exec(select(Notification).where(Notification.uuid == notification_uuid)).first()
        if not q:
            raise HTTPException(status_code=404, detail="Not found")
        q.read = True
        session.add(q)
        session.commit()
        return {"ok": True}

# Endpoint to enqueue arbitrary agent task
@app.post("/agent/enqueue")
async def enqueue_task(task: Dict[str, Any]):
    await agent_manager.enqueue(task)
    return {"enqueued": True}

# ----------------------------
# WebSocket endpoint for real-time updates
# ----------------------------

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    cid = await manager.connect(websocket, client_id)
    try:
        await manager.send_json({"type": "connected", "client_id": cid})
        while True:
            data = await websocket.receive_text()
            # Basic ping/echo handling and simple commands
            if data == "ping":
                await websocket.send_text("pong")
            else:
                # allow clients to ask to run a simple agent task via websocket
                try:
                    import json
                    payload = json.loads(data)
                    # e.g. {"run": "notifier", "message": "hello"}
                    if payload.get("run"):
                        task = payload.get("task", {})
                        await agent_manager.enqueue(task)
                        await websocket.send_text("task enqueued")
                except Exception:
                    await websocket.send_text("ignored")
    except WebSocketDisconnect:
        await manager.disconnect(cid)

# ----------------------------
# A small CLI test runner for demonstration
# ----------------------------

async def demo_flow():
    # enqueue a few demo tasks
    await agent_manager.enqueue({"agent": "notifier-agent", "message": "System demo started"})
    await agent_manager.enqueue({"agent": "property-agent", "action": "classify", "property": {"price": "$600000", "title": "Demo"}})

# ----------------------------
# Dockerfile and README (embedded)
# ----------------------------

DOCKERFILE = r"""
# Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir fastapi uvicorn[standard] sqlmodel sqlalchemy
EXPOSE 8000
CMD ["uvicorn", "AgenticPythonSystem:app", "--host", "0.0.0.0", "--port", "8000"]
"""

REQUIREMENTS = r"""
fastapi
uvicorn[standard]
sqlmodel
"""

README = r"""
AgenticPythonSystem
===================

A single-file FastAPI app demonstrating an "agentic" architecture.

Run locally:

1. python -m pip install -r requirements.txt
2. uvicorn AgenticPythonSystem:app --reload --port 8000

Endpoints:
- GET /health
- GET /properties
- POST /properties {title, location, price, type, beds, baths, area}
- GET /schedules
- POST /schedules {title, time: ISO8601, property_id}
- GET /notifications
- WebSocket: /ws/{client_id}

Architecture notes:
- Agents are simple Python classes implementing `handle`.
- AgentManager runs a single async worker that consumes tasks from an asyncio.Queue.
- NotifierAgent writes to the database and broadcasts over WebSocket.
- Property creation enqueues classification and notification tasks.

Next steps / improvements:
- Add authentication (JWT)
- Replace in-process queue with Redis/RQ/Celery for scale
- Add robust retry/backoff for agents
- Add schema validation for incoming payloads

"""

# ----------------------------
# If module executed directly, start the server
# ----------------------------

if __name__ == '__main__':
    print("Starting demo server... (http://0.0.0.0:8000)")
    # run demo_flow after the loop starts
    async def _main():
        init_db()
        agent_manager.start_background_loop()
        await demo_flow()
        config = uvicorn.Config("AgenticPythonSystem:app", host="0.0.0.0", port=8000, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    asyncio.run(_main())

# ----------------------------
# Attach Dockerfile/requirements/README for convenience in same file (copy out if needed)
# ----------------------------

# Dockerfile (copy and save as Dockerfile):
# ----------------------------
# {dockerfile}
# ----------------------------

# requirements.txt (copy and save as requirements.txt):
# ----------------------------
# {requirements}
# ----------------------------

# README.md (copy and save as README.md):
# ----------------------------
# {readme}
# ----------------------------

# Fill placeholders (so the file contains the actual content if user needs to copy-paste)

_agentic_placeholders = {
    'dockerfile': DOCKERFILE,
    'requirements': REQUIREMENTS,
    'readme': README,
}

# End of file
