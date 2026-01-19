from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
	from dotenv import load_dotenv
except ImportError:
	load_dotenv = None

from routes.text_query import router as text_query_router
from routes.student_onboarding import router as student_router
from routes.usual_routes import router as usual_routes_router
from routes.tourist_routes import router as tourist_router
from routes.transit_routes import router as transit_router
from routes.transcription_routes import router as transcription_router
from routes.translation_routes import router as translation_router
from services.data_loader import StaticDataStore
from services.conversation_state import ConversationStateManager


app = FastAPI(title="Voice Travel Assistant", version="0.1.0")

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


@app.on_event("startup")
async def load_static_data() -> None:
	import os
	
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


@app.get("/health")
async def health() -> dict:
	return {"status": "ok"}


app.include_router(text_query_router)
app.include_router(student_router)
app.include_router(usual_routes_router)
app.include_router(tourist_router)
app.include_router(transit_router)
app.include_router(transcription_router)
app.include_router(translation_router)

