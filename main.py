from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from source.database import get_db, create_db_and_tables
from source.models import User, UserToken, Email

@asynccontextmanager
async def lifespan(app:FastAPI):
    print("INFO:  Starting up and creating database tables...")
    await create_db_and_tables()
    print("INFO:  Database tables created successfully")
    yield
    print("INFO:  Shutting down...")

app= FastAPI(
    title="MAILMATE AI API",
    description="backend for a smart email assistant",
    version="1.0.0",
    lifespan=lifespan,
)

@app.get("/", tags=["Root"])
async def read_root():
    return  {"message":"Welcome to MailMate AI backend"}


@app.get("/db-check", tags=["Health Check"])
async def db_check(db:AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "message":"Database connection is successful"}
    except Exception as e:
        return {"status":"error", "message":f"Database connection failed: {e}"}


@app.get("/tables", tags=["Database Debug"])
async def list_tables(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
    )
    tables = [row[0] for row in result.fetchall()]
    return {"tables": tables}