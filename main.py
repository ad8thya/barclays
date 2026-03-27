from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from services.graph_service import init_db

from routers import score, email, website, attachments, explain
from routes import audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

init_db()

app.include_router(score.router)
app.include_router(email.router)

app.include_router(website.router, tags=["Website"])

app.include_router(attachments.router)
app.include_router(explain.router)
app.include_router(audio.router)

@app.get("/")
def root():
    return {"message": "CrossShield running 🚀"}
