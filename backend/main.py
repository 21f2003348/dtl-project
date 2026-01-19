from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None

from routes.text_query import router as text_query_router
from routes.tourist_routes import router as tourist_router
from routes.transit_routes import router as transit_router
from routes.transcription_routes import router as transcription_router
from routes.translation_routes import router as translation_router
from routes.auth_routes import router as auth_router
from routes.history_routes import router as history_router
from routes.itinerary_routes import router as itinerary_router
from services.data_loader import StaticDataStore
from services.conversation_state import ConversationStateManager
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
	# Startup
	import os
	
	# Initialize database
	init_db()
	
	if load_dotenv:
		# Load from project root or backend dir
		env_path = Path(__file__).parent.parent / ".env"
		if not env_path.exists():
			env_path = Path(__file__).parent / ".env"
		print(f"[STARTUP] Loading .env from: {env_path} (exists: {env_path.exists()})")
		load_dotenv(dotenv_path=env_path, override=True)
		token = os.getenv("TOKEN")
		print(f"[STARTUP] TOKEN loaded: {'Yes' if token else 'No'} (length: {len(token) if token else 0})")
	else:
		print("[STARTUP] python-dotenv not installed, cannot load .env")
	
	base_path = Path(__file__).parent
	store = StaticDataStore(base_path)
	store.load_all()
	app.state.data_store = store
	app.state.state_mgr = ConversationStateManager()
	print("[STARTUP] Static data and state manager initialized")
	
	yield
	# Shutdown
	print("[SHUTDOWN] Shutting down application...")


app = FastAPI(title="Voice Travel Assistant", version="0.1.0", lifespan=lifespan)

# Allow local frontend (e.g., live server on :5500) to call the API
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://127.0.0.1:5500",
		"http://localhost:5500",
		"http://127.0.0.1:3000",
		"http://localhost:3000",
		"http://127.0.0.1",
		"http://localhost",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


app.include_router(text_query_router)
app.include_router(tourist_router)
app.include_router(transit_router)
app.include_router(transcription_router)
app.include_router(translation_router)
app.include_router(auth_router)
app.include_router(history_router)
app.include_router(itinerary_router)

