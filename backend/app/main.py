from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.upload import router as upload_router
from app.api.analysis import router as analysis_router


app = FastAPI(
    title="Autonomous Data Analyst"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(upload_router)
app.include_router(analysis_router)


@app.get("/")
def root():

    return {
        "message": "Autonomous Data Analyst API"
    }