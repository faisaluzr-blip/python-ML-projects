# VeriFact AI: Fake News Detection & Verification Platform

VeriFact AI is a full-stack academic-grade platform for detecting and verifying suspicious news with Python, machine learning, real-time APIs, authentication, history, analytics, and an animated React dashboard.

## Features

- FastAPI backend with JWT auth, password hashing, rate limiting, CORS, input sanitization, and protected admin APIs.
- Machine learning pipeline using TF-IDF with Logistic Regression-style, Passive Aggressive-style, and Naive Bayes classifiers that run locally on Python 3.14. Optional scikit-learn dependencies are listed for Python 3.10-3.12 extension work.
- Automatic model comparison, saved `.pkl` artifact, sample dataset, and retraining endpoint.
- Prediction support for pasted text, uploaded `.txt` files, and article URLs.
- AI explanation engine with clickbait, emotional manipulation, suspicious sentence, sentiment, keyword, summary, and trust-score signals.
- Real-time verification via NewsAPI when `NEWS_API_KEY` is configured, with offline trusted-source fixtures for local use.
- SQLAlchemy database using SQLite by default and PostgreSQL through `DATABASE_URL`.
- React + Vite + Tailwind + Framer Motion + Recharts frontend with dashboard, detector, chatbot, profile, admin panel, dark/light theme, responsive layout, loading states, and notifications.

## Project Structure

```text
backend/
  app/
    api/             REST routers
    core/            config, database, security
    models/          SQLAlchemy tables
    schemas/         Pydantic schemas
    services/        ML, NLP, verification logic
  data/sample_news.csv
  ml/train.py
  requirements.txt
  storage/           generated db and model files
frontend/
  src/
    components/
    context/
    lib/
    pages/
    styles/
```

## Setup

### 1. Backend

```powershell
cd "C:\Users\MD_FAISAL\PycharmProjects\AI-Powered Fake News Detection & Verification Platform"
python -m venv .venv
.\.venv\Scripts\activate
pip install -r backend\requirements.txt
copy .env.example .env
python backend\ml\train.py
python main.py
```

Backend runs at `http://127.0.0.1:8000`.

API docs are available at `http://127.0.0.1:8000/docs`.

### 2. Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend runs at `http://127.0.0.1:5173`.

## Demo Accounts

- Admin: `admin@verifact.ai` / `admin123`
- Student: `student@verifact.ai` / `student123`

Demo users are created automatically at backend startup.

## PostgreSQL

Set `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/verifact
```

Then restart the backend. Tables are created automatically.

Install a PostgreSQL driver when your Python environment supports it:

```powershell
pip install -r backend\requirements-postgres.txt
```

## Live News Verification

The platform works offline using trusted source fixtures. For real headlines, create a NewsAPI key and set:

```env
NEWS_API_KEY=your_key_here
```

## Testing

```powershell
# Backend smoke test
python -m compileall backend
python backend\ml\train.py

# Frontend production build
cd frontend
npm run build
```

## Optional Scikit-Learn Stack

The included backend runs on the current Python 3.14 environment without compiled ML wheels. If you use Python 3.10-3.12 and want pandas/scikit-learn installed for experimentation, run:

```powershell
pip install -r backend\requirements-ml-scikit.txt
```

## Main Endpoints

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/predictions`
- `POST /api/predictions/upload`
- `GET /api/predictions/history`
- `GET /api/predictions/metrics`
- `POST /api/verification`
- `GET /api/analytics`
- `GET /api/admin/users`
- `POST /api/admin/retrain`
- `POST /api/smart/chat`

## Custom Dataset

Replace or extend `backend/data/sample_news.csv` with:

```csv
label,text
REAL,"verified article text"
FAKE,"misleading article text"
```

Then run:

```powershell
python backend\ml\train.py
```
