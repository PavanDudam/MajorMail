# app/main.py
import os
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request, HTTPException, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from starlette.middleware.sessions import SessionMiddleware
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware

# This line tells the OAuth library to allow insecure HTTP transport for local development.
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

# Corrected imports to match your project structure
from source import auth, crud, gmail_service, ai_service, models
from source.database import create_db_and_tables, get_db, AsyncSessionLocal


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("INFO:     Starting up...")
    await create_db_and_tables()
    print("INFO:     Database tables created.")
    yield
    print("INFO:     Shutting down.")


app = FastAPI(title="MailMate AI API", lifespan=lifespan)

# --- THE FIX: Add the CORS Middleware ---
# This tells the backend to allow requests from any origin.
# For production, you would restrict this to your actual frontend's domain.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows all origins
    allow_credentials=True,
    allow_methods=["*"], # Allows all methods
    allow_headers=["*"], # Allows all headers
)

app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))


# --- Helper function for background task ---
async def process_single_email(email_id: int, user_email: str):
    """
    A helper function that runs in the background. It creates its own DB session,
    processes an email, and then closes the session.
    """
    # Use a unique variable name 'session' to avoid scope conflicts
    session = AsyncSessionLocal()
    try:
        email = await session.get(models.Email, email_id)
        if not email or not email.body:
            return

        # --- Summarization Step ---
        if not email.summary:
            summary = await run_in_threadpool(ai_service.summarize_text, email.body)
            await crud.update_email_summary(session, email_id, summary)

        # --- Categorization Step ---
        if email.category == "Uncategorized":
            full_text = f"{email.subject} {email.body}"
            category = await run_in_threadpool(ai_service.classify_email, full_text)
            await crud.update_email_category(session, email_id, category)

        # --- Priority Scoring Step ---
        email_data = {
            "subject": email.subject,
            "body": email.body,
            "sender": email.sender,
        }
        score = await run_in_threadpool(
            ai_service.calculate_priority_score, email_data, user_email
        )
        await crud.update_email_priority(session, email_id, score)
        
        # --- NEW FEATURE: Action Engine Step ---
        action = await run_in_threadpool(ai_service.determine_action, full_text, category)
        if action: # Only update if an action was determined
            await crud.update_email_action(session, email_id, action)

        # --- Commit all staged changes for this email at the end ---
        await session.commit()
        print(f"INFO:     Successfully processed and committed email ID: {email_id}")

    except Exception as e:
        print(f"ERROR:    Failed to process email ID {email_id}: {e}")
        traceback.print_exc()
        await session.rollback()
    finally:
        await session.close()


# --- API Endpoints ---
@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to MailMate AI backend"}


@app.get("/db-check", tags=["Health Check"])
async def db_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ok", "message": "Database connection is successful"}
    except Exception as e:
        return {"status": "error", "message": f"Database connection failed: {e}"}


@app.get("/auth/login", tags=["Authentication"])
async def login_with_google(request: Request):
    flow = auth.create_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type="offline", prompt="consent"
    )
    request.session["state"] = state
    return RedirectResponse(url=authorization_url)


@app.get("/auth/callback", tags=["Authentication"])
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    state = request.session.get("state")
    if not state or state != request.query_params.get("state"):
        return JSONResponse(
            status_code=400, content={"message": "State mismatch error."}
        )
    flow = auth.create_oauth_flow()
    try:
        await run_in_threadpool(
            flow.fetch_token, authorization_response=str(request.url)
        )
        if not flow.credentials or not flow.credentials.token:
            return JSONResponse(
                status_code=500,
                content={"message": "Failed to fetch token from Google."},
            )

        credentials = flow.credentials
        user_info = await run_in_threadpool(auth.get_google_user_info, credentials)
        user = await crud.get_or_create_user(db, user_info)
        token_data = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
        }
        await crud.save_user_token(db, user, token_data)
        # Instead of returning JSON, redirect to frontend with email
        frontend_url = f"http://localhost:5173/?email={user.email}"
        return RedirectResponse(url=frontend_url)

    except Exception as e:
        print("--- AUTHENTICATION ERROR: FULL TRACEBACK ---")
        traceback.print_exc()
        print("--------------------------------------------")
        return JSONResponse(
            status_code=500, content={"message": "Authentication failed."}
        )


@app.get("/emails/fetch/{user_email}", tags=["Emails"])
async def fetch_emails(user_email: str, db: AsyncSession = Depends(get_db)):
    user = await crud.get_user_by_email(db, email=user_email)
    if not user or not user.tokens:
        raise HTTPException(
            status_code=404, detail="User or user tokens not found. Please login first"
        )

    credentials = auth.rebuild_credentials(user.tokens[0])
    service = gmail_service.get_gmail_service(credentials)
    messages = await run_in_threadpool(gmail_service.fetch_email_list, service)
    if not messages:
        return {"message": "NO new emails found."}

    fetched_count = 0
    for message in messages:
        raw_email = await run_in_threadpool(
            gmail_service.fetch_email_details, service, message["id"]
        )
        parsed_email = gmail_service.parse_email(raw_email)
        if parsed_email:
            await crud.create_email(db, user, parsed_email)
            fetched_count += 1

    return {"message": f"Successfully fetched and saved {fetched_count} emails."}


# --- Single, Corrected Processing Endpoint ---
@app.post("/emails/process/{user_email}", tags=["AI Processing"])
async def process_emails(
    user_email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    user = await crud.get_user_by_email(db, email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    emails_to_process = await crud.get_unprocessed_emails(db, user)
    if not emails_to_process:
        return {"message": "No new emails to process."}

    # Correctly pass user.email to the background task
    for email in emails_to_process:
        background_tasks.add_task(process_single_email, email.id, user.email)

    return {
        "message": f"Started processing {len(emails_to_process)} emails in the background."
    }

#day-8
@app.get("/emails/{user_email}", response_model=List[models.EmailRead], tags=["Emails"])
async def get_emails(
    user_email: str, 
    category: Optional[str] = None, # This is an optional query parameter
    db: AsyncSession = Depends(get_db)
):
    """
    Fetches all processed emails for a user, sorted by priority.
    Optionally filters by category (e.g., ?category=Work).
    """
    user = await crud.get_user_by_email(db, email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    emails = await crud.get_emails_for_user(db, user, category=category)
    return emails

# --- NEW FEATURE: Dossier Endpoint ---
@app.get("/dossier/{user_email}", response_model=models.SenderDossier, tags=["Dossier"])
async def get_sender_dossier(
    user_email: str,
    sender_email: str, # This is a required query parameter
    db: AsyncSession = Depends(get_db)
):
    """
    Provides a summary of all interactions with a specific sender.
    Example: /dossier/user@example.com?sender_email=boss@work.com
    """
    user = await crud.get_user_by_email(db, email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    dossier_data = await crud.get_dossier_for_sender(db, user, sender_email)
    
    if dossier_data["total_emails"] == 0:
        raise HTTPException(status_code=404, detail=f"No emails found from sender: {sender_email}")
        
    return dossier_data
