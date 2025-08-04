# app/crud.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlmodel import select
from . import models

async def get_or_create_user(db: AsyncSession, user_info: dict) -> models.User:
    """
    A helper function that checks if a user exists.
    If they do, it returns the user. If not, it creates them.
    This version eagerly loads the 'tokens' relationship to prevent lazy loading issues.
    """
    statement = (
        select(models.User)
        .where(models.User.email == user_info['email'])
        .options(selectinload(models.User.tokens)) # <-- THE FIX: Eagerly load the tokens
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
    """
    # --- THE FIX: Instead of checking user.tokens, we explicitly query for existing tokens ---
    # This avoids the lazy loading issue entirely.
    existing_tokens_statement = select(models.UserToken).where(models.UserToken.user_id == user.id)
    results = await db.execute(existing_tokens_statement)
    
    # Delete any old tokens we find
    for token in results.scalars().all():
        await db.delete(token)
    
    await db.commit()
    # --------------------------------------------------------------------------------------

    # Create the new token record
    new_token = models.UserToken(
        user_id=user.id,
        access_token=token_data['access_token'],
        refresh_token=token_data.get('refresh_token')
    )
    db.add(new_token)
    await db.commit()
    print(f"Tokens saved for user {user.email}")

