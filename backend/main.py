from contextlib import asynccontextmanager
from pdb import run
from pyexpat.errors import messages
from source import gmail_service
from source import ai_service
from fastapi import FastAPI, Depends, Request, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from source.database import get_db, create_db_and_tables
from source.models import User, UserToken, Email
from source import auth, crud, ai_service, models
import os
import traceback

from fastapi.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

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

app.add_middleware(SessionMiddleware, secret_key=os.urandom(24))

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




@app.get("/auth/login", tags=["Authentication"])
async def login_with_google(request:Request):
    """
    Redirects the user to the Google consent page to start the OAuth flow.
    """

    flow = auth.create_oauth_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        prompt='consent'
    )

    request.session['state'] = state

    return RedirectResponse(url=authorization_url)

@app.get("/auth/callback", tags=["Authentication"])
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handles the callback from Google after the user grants permission.
    """
    state = request.session.get('state')
    if not state or state != request.query_params.get('state'):
        return JSONResponse(status_code=400, content={"message": "State mismatch error."})

    flow = auth.create_oauth_flow()
    
    try:
        # --- FIX: Pass the function and its arguments directly to run_in_threadpool ---
        await run_in_threadpool(
            flow.fetch_token, 
            authorization_response=str(request.url)
        )
        # --------------------------------------------------------------------------

        # --- DEBUGGING: Add a check to ensure credentials and token exist ---
        if not flow.credentials or not flow.credentials.token:
            print("ERROR: Credentials or token not found after fetch_token call.")
            return JSONResponse(
                status_code=500, 
                content={"message": "Failed to fetch token from Google."}
            )
        # --------------------------------------------------------------------

        credentials = flow.credentials
        
        # --- FIX: Do the same for the second blocking call ---
        user_info = await run_in_threadpool(
            auth.get_google_user_info, 
            credentials
        )
        # ----------------------------------------------------

        # The rest of the code is already async and can run normally
        user = await crud.get_or_create_user(db, user_info)
        token_data = {
            'access_token': credentials.token,
            'refresh_token': credentials.refresh_token,
        }
        await crud.save_user_token(db, user, token_data)
        
        return {"message": f"Successfully authenticated as {user.email}"}

    except Exception as e:
        # --- DEBUGGING: Add full traceback for detailed error logging ---
        print("--- AUTHENTICATION ERROR: FULL TRACEBACK ---")
        traceback.print_exc()
        print("--------------------------------------------")
        # ----------------------------------------------------------------        
        print(f"An error occurred during authentication: {e}")
        return JSONResponse(status_code=500, content={"message": "Authentication failed."})

@app.get("/emails/fetch/{user_email}", tags=['Emails'])
async def fetch_emails(user_email:str, db:AsyncSession=Depends(get_db)):
    """
    Fetches recent emails for a given user and stores them in the database.
    """
    #1.Get user and their tokens
    user = await crud.get_user_by_email(db, email=user_email)
    if not user or not user.tokens:
        raise HTTPException(status_code=404, detail="User or user tokens not found. Please login first")
    
    #2. Rebuild Credentials
    credentials=auth.rebuild_credentials(user.tokens[0])

    #3. Connect to gmail service
    service=gmail_service.get_gmail_service(credentials)

    #4. Fetch list of  email IDs
    messages=await run_in_threadpool(gmail_service.fetch_email_list, service)
    if not messages:
        return {"message":"NO new emails found."}
    
    #5. Fetch, Parse,  and save each email
    fetched_count = 0
    for message in messages:
        raw_email=await run_in_threadpool(gmail_service.fetch_email_details, service, message['id'])
        parsed_email = gmail_service.parse_email(raw_email)
        if parsed_email:
            await crud.create_email(db, user, parsed_email)
            fetched_count += 1
        
    return {"message": f"Successfully fetched and saved {fetched_count} emails."}

async def process_single_email_summary(email_id: int, db: AsyncSession):
    """
    A helper function that can be run in the background.
    It fetches an email, generates a summary, and saves it.
    """
    email = await db.get(models.Email, email_id)
    if email and email.body:
        # Run the slow AI model in a threadpool to not block the async event loop
        summary = await run_in_threadpool(ai_service.summarize_text, email.body)
        await crud.update_email_summary(db, email_id, summary)


@app.post("/emails/process/{user_email}", tags=["AI Processing"])
async def process_emails(
    user_email: str, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Finds unprocessed emails for a user and starts background tasks to summarize them.
    """
    user = await crud.get_user_by_email(db, email=user_email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    emails_to_process = await crud.get_unprocessed_emails(db, user)
    if not emails_to_process:
        return {"message": "No new emails to process."}

    # Add a background task for each email
    for email in emails_to_process:
        background_tasks.add_task(process_single_email_summary, email.id, db)
        
    return {
        "message": f"Started processing {len(emails_to_process)} emails in the background."
    }
