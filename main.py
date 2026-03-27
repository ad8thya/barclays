from fastapi import FastAPI
from routers import website

app = FastAPI()

# register router
app.include_router(website.router, prefix="/website", tags=["Website"])

@app.get("/")
def root():
    return {"message": "CrossShield running 🚀"}