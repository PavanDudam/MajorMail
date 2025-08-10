📬 MailMate AI - Backend API

MailMate AI is the backend service for a smart, Gmail-integrated web application designed to solve email overload. It uses AI and ML to intelligently categorize, summarize, and prioritize a user's emails, transforming a cluttered inbox into a productivity-focused smart assistant.

This repository contains the complete backend built with FastAPI.
✨ Core Features

    Secure Google OAuth 2.0 Login: Users authenticate securely with their Google accounts without the app ever storing their passwords.

    Gmail API Integration: Fetches raw email data (subject, sender, body, etc.) directly from the user's inbox.

    AI-Powered Summarization: Uses a Hugging Face transformers model (distilbart-cnn-12-6) to generate concise, 2-line summaries for long emails.

    ML Smart Tagging: A custom keyword-based classifier automatically assigns emails to useful categories like Work, Promotions, Finance, Social, and more.

    Priority Scoring Engine: A rule-based algorithm analyzes email content to assign a priority score, enabling a "Priority-First" inbox experience.

    Asynchronous Background Processing: All heavy AI/ML tasks are run as background jobs using FastAPI's BackgroundTasks, ensuring the API remains fast and responsive.

🛠️ Technology Stack

    Framework: FastAPI

    Database: Neon DB (Cloud PostgreSQL)

    ORM / Data Validation: SQLModel

    Database Driver: asyncpg

    AI / ML: Hugging Face transformers, scikit-learn, torch

    Authentication: google-auth-oauthlib, google-api-python-client

    Package Manager: uv

🚀 Getting Started

Follow these steps to set up and run the project locally.
1. Prerequisites

    Python 3.9+

    uv package installer (pip install uv)

    A free Neon DB account.

    A Google Cloud Platform account.

2. Google Cloud Setup

    Create a new project in the Google Cloud Console.

    Enable the Gmail API.

    Go to APIs & Services > Credentials.

    Create an OAuth 2.0 Client ID for a "Web application".

    Add http://127.0.0.1:8000/auth/callback to the "Authorized redirect URIs".

    Copy the Client ID and Client Secret.

3. Local Project Setup

    Clone the repository (or set up the project folder):

    git clone <your-repo-url>
    cd mailmate-ai-backend

    Create and activate a virtual environment:

    uv venv

    Install all dependencies:

    uv pip install "fastapi[all]" sqlmodel asyncpg python-dotenv google-auth-oauthlib google-api-python-client transformers torch scikit-learn

    Configure Environment Variables:

        Create a file named .env in the project root.

        Add your credentials to it:

        # Neon DB Connection String (remember to change postgres:// to postgresql+asyncpg://)
        DATABASE_URL="postgresql+asyncpg://YOUR_NEON_DB_CONNECTION_STRING"

        # Google OAuth Credentials
        GOOGLE_CLIENT_ID="YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com"
        GOOGLE_CLIENT_SECRET="YOUR_GOOGLE_CLIENT_SECRET"

4. Running the Application

    Start the FastAPI server:

    uvicorn app.main:app --reload

    The application will be running at http://127.0.0.1:8000.

    The interactive API documentation (Swagger UI) is available at http://127.0.0.1:8000/docs.

📚 API Endpoints

The core workflow is as follows:

    GET /auth/login: Redirects the user to Google to log in. (Must be accessed directly in the browser).

    GET /emails/fetch/{user_email}: After login, run this to populate the database with the user's raw emails.

    POST /emails/process/{user_email}: Run this to start the background tasks for summarization, categorization, and priority scoring.

    GET /emails/{user_email}: This is the main endpoint to retrieve the fully processed and sorted emails.

        Filtering: You can filter by category using a query parameter, e.g., GET /emails/user@example.com?category=Work. The filter is case-insensitive.