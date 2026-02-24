from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from models import Base
# Import database to create tables
from database import engine
from routers.bracket import bracket_router
# Import routers
from routers.manual_user import manual_participant_router
from routers.user import user_router
from routers.team import team_router
from routers.tournament import tournament_router
from routers.auth import auth_router
from routers import tournament
# Create all database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Tournament API",
    version="1.0.0",
    description="Backend for Tournament Management System"
)

# CORS settings
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def root():
    return {"message": "Backend is running!"}

# Include routers
app.include_router(user_router, prefix="/users", tags=["Users"])
app.include_router(manual_participant_router, prefix="/manual_participants", tags=["Manual Participants"])
app.include_router(tournament_router, prefix="/tournaments", tags=["Tournaments"])
app.include_router(tournament.tournament_router, prefix="/tournaments")
app.include_router(team_router, prefix="/teams", tags=["Teams"])
app.include_router(auth_router, prefix="/auth", tags=["Auth"])
app.include_router(bracket_router, prefix="/matches", tags=["Matches"])