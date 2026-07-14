import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from routers import auth, users, halaqas, posts, goals, questions

# Schema is managed by Alembic migrations ("alembic upgrade head"), not create_all.

logger = logging.getLogger("halqa")

app = FastAPI(title="Halqa App")

# comma-separated env var in production (Vercel URL); any localhost port in dev
ALLOWED_ORIGINS = [o for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(halaqas.router)
app.include_router(posts.router)
app.include_router(posts.comments_router)
app.include_router(goals.router)
app.include_router(questions.router)
app.include_router(questions.answers_router)


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    logger.warning("Integrity error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=409,
        content={"detail": "Request conflicts with existing data"},
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error("Database error on %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Database error"})


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled error on %s %s", request.method, request.url.path, exc_info=exc
    )
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/")
def home():
    return {"message": "Halqa app is running"}
