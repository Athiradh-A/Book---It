from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, resources, bookings, events, analytics, allocation, buildings, amenities, event_registration, event_workflow
from app.core.websocket import manager
from app.api.deps import get_current_user

app = FastAPI(title="Intelligent Campus Room Allocation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(resources.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(events.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(allocation.router, prefix="/api")
app.include_router(buildings.router, prefix="/api")
app.include_router(amenities.router, prefix="/api")
app.include_router(event_registration.router, prefix="/api")
app.include_router(event_workflow.router, prefix="/api")

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo or handle messages
            await websocket.send_text(f"Message received: {data}")
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)

@app.get("/")
async def root():
    return {"message": "Campus Room Allocation API is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

