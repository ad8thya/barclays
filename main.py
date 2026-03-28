from fastapi import FastAPI
from routers.attachments import router as attachments_router

app = FastAPI()

app.include_router(attachments_router)