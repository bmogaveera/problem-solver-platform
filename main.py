from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.auth import router as auth_router
from app.routes.claims import router as claims_router
from app.routes.comments import router as comments_router
from app.routes.problems import router as problems_router
from app.routes.reports import router as reports_router
from app.routes.solutions import router as solutions_router
from app.routes.verification import router as verification_router

app = FastAPI(title="Problem Solver Platform")

# Allow your frontend (running on a different port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your real frontend URL before deploying
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(problems_router)
app.include_router(verification_router)
app.include_router(claims_router)
app.include_router(solutions_router)
app.include_router(comments_router)
app.include_router(reports_router)


@app.get("/")
def root():
    return {"status": "Problem Solver Platform API is running"}
