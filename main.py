from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from services.oob_service import init_oob_table
from routers import ocr   # add this import

from routers import score, email, website, attachments, explain
from routes import audio

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

try:
    from services.graph_service import init_db
    init_db()
except ImportError:
    print("Graph service not available, skipping init.")

init_oob_table()

app.include_router(score.router)
app.include_router(email.router)
app.include_router(website.router, tags=["Website"])
app.include_router(attachments.router)
app.include_router(explain.router)
app.include_router(audio.router)
app.include_router(ocr.router)  # add this line


@app.get("/")
def root():
    return {"message": "CrossShield running 🚀"}

