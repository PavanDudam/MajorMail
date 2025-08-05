# app/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from source import models

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
