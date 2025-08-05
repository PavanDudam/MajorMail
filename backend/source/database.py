# app/database.py

import os
from dotenv import load_dotenv
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("No DATABASE_URL set for the connection")

# --- THE DEFINITIVE FIX: Disable statement caching for the asyncpg driver ---
# This prevents all caching errors when tables are frequently dropped and recreated.
engine = create_async_engine(
    DATABASE_URL, 
    connect_args={"statement_cache_size": 0}
)
# -------------------------------------------------------------------------

# This function will create all database tables based on SQLModel metadata
async def create_db_and_tables():
    """
    Initializes the database and creates tables.
    """
    async with engine.begin() as conn:
        # --- DEVELOPMENT ONLY: This wipes the database on every restart ---
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

# Create a configured "Session" class
AsyncSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)

# Dependency to get a DB session for API endpoints
async def get_db():
    """
    Dependency that provides a database session for a request.
    """
    async with AsyncSessionLocal() as session:
        yield session
