# 📩 MailMate AI - Complete Setup Guide

A comprehensive guide to set up and run the MailMate AI project on any system.

## 🛠️ Prerequisites
- **Python 3.8+**
- **Node.js 16+** 
- **PostgreSQL 13+**
- **Git**

## 📥 Step 1: Clone & Setup
```bash
# Clone project
git clone <your-repo-url>
cd mailmate-ai

# Or extract downloaded zip and navigate
cd mailmate-ai
```

## 🗄️ Step 2: Database Setup

### Install PostgreSQL
**Windows:** Download from https://www.postgresql.org/download/windows/
**macOS:** `brew install postgresql && brew services start postgresql`
**Linux:** `sudo apt install postgresql postgresql-contrib`

### Create Database
```bash
psql -U postgres -c "CREATE DATABASE mailmate;"
psql -U postgres -c "CREATE USER mailmate_user WITH PASSWORD 'mailmate123';"
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE mailmate TO mailmate_user;"
```

## 🔧 Step 3: Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install fastapi uvicorn sqlmodel sqlalchemy asyncpg python-dotenv google-auth-oauthlib google-auth-httplib2 google-api-python-client transformers sentence-transformers torch requests-oauthlib

# Create environment file
echo "DATABASE_URL=postgresql+asyncpg://mailmate_user:mailmate123@localhost:5432/mailmate" > .env
echo "GOOGLE_CLIENT_ID=your_client_id_here" >> .env
echo "GOOGLE_CLIENT_SECRET=your_client_secret_here" >> .env
```

## 🌐 Step 4: Google Cloud Setup

1. **Go to** [Google Cloud Console](https://console.cloud.google.com/)
2. **Create project** or select existing
3. **Enable APIs**: Gmail API & Google+ API
4. **Configure OAuth Consent Screen**:
   - App name: `MailMate AI`
   - User type: External
   - Add scopes: `../auth/gmail.readonly`, `../auth/userinfo.email`, `../auth/userinfo.profile`
   - Add your email as **Test User**
5. **Create Credentials**:
   - OAuth 2.0 Client IDs
   - Web application
   - Redirect URIs: `http://127.0.0.1:8000/auth/callback`
6. **Copy Client ID & Secret** to `.env` file

## ⚡ Step 5: Frontend Setup
```bash
cd ../frontend
npm install
```

## 🚀 Step 6: Run Application

### Terminal 1 - Backend:
```bash
cd backend
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
uvicorn source.main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

## 🧪 Step 7: Test & Use

1. **Open:** http://localhost:5173
2. **Click:** "Login with Google"
3. **Complete OAuth flow**
4. **Use workflow:**
   - Fetch from Gmail → Process Emails → Refresh Inbox
   - Use "Sender Dossier" for analytics
   - Use "Direct Conversations" for raw email threads

## 🐛 Troubleshooting

### Database Issues:
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql  # Linux
net start postgresql-x64-13      # Windows
```

### Port Issues:
```bash
# Kill process on port 8000
npx kill-port 8000
```

### Dependency Issues:
```bash
# Backend
deactivate && rm -rf venv && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Frontend  
rm -rf node_modules && npm install
```

## 📁 Project Structure
```
mailmate-ai/
├── backend/source/     # FastAPI + AI processing
├── frontend/src/       # React frontend
└── README.md
```

## 🔗 URLs
- **Frontend:** http://localhost:5173
- **Backend:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs

## ⚠️ Important Notes
- First run will download AI models (~2GB, takes 5-10 minutes)
- Ensure PostgreSQL is running before starting backend
- Use same Google account for OAuth that you added as test user
- Allow all permissions during OAuth consent

**Need help?** Check terminal logs for error messages and ensure all services are running! 🚀