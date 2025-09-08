from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from source import models
from typing import Optional
from sqlalchemy import func
from collections import Counter
from datetime import datetime, timedelta

async def get_user_by_email(db: AsyncSession, email: str) -> models.User | None:
    """
    Fetches a single user from the database by their email address.
    This version eagerly loads the 'tokens' relationship.
    """
    statement = (
        select(models.User)
        .where(models.User.email == email)
        .options(selectinload(models.User.tokens))
    )
    result = await db.execute(statement)
    return result.scalar_one_or_none()

async def get_or_create_user(db: AsyncSession, user_info: dict) -> models.User:
    """
    A helper function that checks if a user exists.
    If they do, it returns the user. If not, it creates them.j
    This version eagerly loads the 'tokens' relationship to prevent lazy loading issues.
    """
    statement = (
        select(models.User)
        .where(models.User.email == user_info['email'])
        .options(selectinload(models.User.tokens))
    )
    result = await db.execute(statement)
    user = result.scalar_one_or_none()
    
    if user:
        print(f"User {user.email} found in database.")
        return user
    
    print(f"User {user_info['email']} not found. Creating new user.")
    new_user = models.User(
        email=user_info['email'],
        full_name=user_info.get('name', '')
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def save_user_token(db: AsyncSession, user: models.User, token_data: dict):
    """
    Saves or updates the OAuth tokens for a specific user.
    This version is robust and works for both new and existing users.
    """
    # --- THE DEFINITIVE FIX: ---
    # Instead of checking `if user.tokens:`, which causes lazy loading errors on new users,
    # we explicitly query for existing tokens based on the user's ID. This is safe.
    
    # 1. Find any existing tokens for this user.
    existing_tokens_statement = select(models.UserToken).where(models.UserToken.user_id == user.id)
    results = await db.execute(existing_tokens_statement)
    
    # 2. Delete them.
    for token in results.scalars().all():
        await db.delete(token)
    
    # This commit is important to finalize the deletion before adding the new token.
    await db.commit()
    # --------------------------------------------------------------------------------------

    # 3. Create the new token record.
    new_token =     models.UserToken(
        user_id=user.id,
        access_token=token_data['access_token'],
        refresh_token=token_data.get('refresh_token')
    )
    db.add(new_token)
    await db.commit()
    print(f"Tokens saved for user {user.email}")

async def create_email(db: AsyncSession, owner: models.User, email_data: dict):
    """
    Saves a new email to the database, avoiding duplicates.
    """
    statement = select(models.Email).where(models.Email.message_id == email_data['message_id'])
    results = await db.execute(statement)

    if results.scalar_one_or_none():
        print(f"Email {email_data['message_id']} already exists. Skipping.")
        return

    new_email = models.Email(
        owner_id=owner.id,
        message_id=email_data['message_id'],
        subject=email_data['subject'],
        sender=email_data['sender'],
        body=email_data['body'],
        received_at=email_data['received_at']
    )
    db.add(new_email)
    await db.commit()
    print(f"Saved new email from {new_email.sender} with subject: {new_email.subject}")


async def get_unprocessed_emails(db:AsyncSession, user:models.User)->list[models.Email]:
    """
    Fetches all emails for a user that have not yet been summarized.
    """
    statement = (
        select(models.Email)
        .where(models.Email.owner_id == user.id)
        .where(models.Email.summary == None)
    )
    
    results = await db.execute(statement)
    return results.scalars().all()

async def update_email_summary(db:AsyncSession, email_id:int, summary:str):
    """
    Updates a specific email in the database with its new summary.
    """
    email_to_update = await db.get(models.Email, email_id)
    if email_to_update:
        email_to_update.summary = summary
        db.add(email_to_update)
        await db.commit()
        print(f"INFO:     Updated summary for email ID: {email_id}")

async def update_email_category(db: AsyncSession, email_id: int, category: str):
    """Stages an update to an email's category. Does NOT commit."""
    email_to_update = await db.get(models.Email, email_id)
    if email_to_update:
        email_to_update.category = category
        db.add(email_to_update)
        print(f"INFO:     Staged category update for email ID: {email_id} to '{category}'")
        
async def update_email_priority(db: AsyncSession, email_id: int, score: int):
    """
    Stages an update to an email's priority score. Does NOT commit.
    """
    email_to_update = await db.get(models.Email, email_id)
    if email_to_update:
        email_to_update.priority_score = score
        db.add(email_to_update)
        print(f"INFO:     Staged priority score update for email ID: {email_id} to {score}")
        
async def get_emails_for_user(
    db: AsyncSession, 
    user: models.User, 
    category: Optional[str] = None
) -> list[models.Email]:
    """
    Fetches all emails for a user, sorted by priority, with an optional category filter.
    """
    statement = (
        select(models.Email)
        .where(models.Email.owner_id == user.id)
        .order_by(models.Email.priority_score.desc(), models.Email.received_at.desc())
    )
    
    # If a category is provided, add it as a filter to the query
    if category:
        # We convert both the database column and the user's input to lowercase
        statement = statement.where(func.lower(models.Email.category) == category.lower())
        
    results = await db.execute(statement)
    return results.scalars().all()

async def update_email_action(db: AsyncSession, email_id: int, action: str | None):
    """
    Stages an update to an email's suggested action. Does NOT commit.
    """
    email_to_update = await db.get(models.Email, email_id)
    if email_to_update:
        email_to_update.suggested_action = action
        db.add(email_to_update)
        print(f"INFO:     Staged action update for email ID: {email_id} to '{action}'")

async def get_dossier_for_sender(
    db: AsyncSession, 
    user: models.User, 
    search_query: str  # Changed from sender_address to search_query
) -> dict:
    """
    Smart search for dossier - works with names or email parts.
    """
    print(f"DEBUG: Smart searching for: '{search_query}'")
    
    # Calculate date range for last 6 months
    six_months_ago = datetime.utcnow() - timedelta(days=180)
    
    # Smart search: look for the query anywhere in sender field
    statement = (
        select(models.Email)
        .where(models.Email.owner_id == user.id)
        .where(models.Email.sender.ilike(f"%{search_query}%"))  # Partial match anywhere
        .where(models.Email.received_at >= six_months_ago)
        .order_by(models.Email.received_at.desc())
    )
    
    results = await db.execute(statement)
    sender_emails = results.scalars().all()
    
    print(f"DEBUG: Found {len(sender_emails)} emails matching '{search_query}'")
    
    # ... rest of your existing dossier code ...
    
    if not sender_emails:
        return {
            "total_emails": 0,
            "category_counts": {},
            "average_priority_score": 0,
            "latest_email_summary": None,
            "most_common_action": None,
            "conversation_history": [],
            "period_covered": "No emails found in last 6 months"
        }

    total_emails = len(sender_emails)
    
    # Calculate category counts
    category_counts = Counter(email.category for email in sender_emails)
    
    # Calculate average priority score
    total_priority = sum(email.priority_score for email in sender_emails)
    average_priority_score = round(total_priority / total_emails, 2) if total_emails > 0 else 0

    # Get the summary of the most recent email
    latest_email_summary = sender_emails[0].summary

    # Find the most common suggested action
    actions = [email.suggested_action for email in sender_emails if email.suggested_action]
    most_common_action = Counter(actions).most_common(1)[0][0] if actions else "None"
    
    # Build conversation history with dates
    conversation_history = []
    for email in sender_emails:
        conversation_history.append({
            "subject": email.subject or "No Subject",
            "summary": email.summary,
            "received_at": email.received_at.isoformat() if email.received_at else None,
            "suggested_action": email.suggested_action
        })
    
    # Determine date range covered
    oldest_email = sender_emails[-1].received_at if sender_emails else None
    newest_email = sender_emails[0].received_at if sender_emails else None
    
    if oldest_email and newest_email:
        period_covered = f"{oldest_email.strftime('%b %d, %Y')} to {newest_email.strftime('%b %d, %Y')}"
    else:
        period_covered = "Date range not available"
    
    return {
        "total_emails": total_emails,
        "category_counts": dict(category_counts),
        "average_priority_score": average_priority_score,
        "latest_email_summary": latest_email_summary,
        "most_common_action": most_common_action,
        "conversation_history": conversation_history,
        "period_covered": period_covered
    }