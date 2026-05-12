# Finance Intelligence Platform

A complete AI-powered finance manager built with Python, FastAPI, SQLite, local ML-style intelligence services, JWT authentication, and a responsive futuristic dashboard UI.

## Features

- Secure signup/login with PBKDF2 password hashing and JWT tokens
- Smart income and expense tracking with AI category prediction
- Receipt upload parsing for OCR-style bill extraction
- Voice-enabled transaction entry through browser speech recognition
- Real-time dashboard updates through server-sent events
- Monthly analytics, animated charts, forecasts, and trend views
- Budget planner with overspending alerts
- Financial health score and spending behavior analysis
- Fraud/anomaly detection for unusual transactions
- Savings goals and subscription/payment reminders
- Multi-currency profile support
- CSV, Excel-compatible, and PDF-style report exports
- Admin dashboard for platform overview
- Dark/light mode, glassmorphism UI, responsive layout

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python run.py
```

Open `http://127.0.0.1:8765`.

Demo credentials:

```text
demo@finance.ai
Demo@12345
```

## Configuration

Copy `.env.example` to `.env` and change `JWT_SECRET` before deployment.

```powershell
Copy-Item .env.example .env
```

The default database is SQLite at `finance.db`. The code is modular so it can be moved to PostgreSQL/MySQL by replacing the database adapter with SQLAlchemy or another production driver.

## API Overview

- `POST /api/auth/signup`
- `POST /api/auth/login`
- `GET /api/dashboard`
- `GET/POST /api/transactions`
- `POST /api/transactions/voice`
- `POST /api/ocr/receipt`
- `GET/POST /api/budgets`
- `GET/POST /api/goals`
- `GET/POST /api/reminders`
- `POST /api/assistant`
- `GET /api/export/{csv|excel|pdf}`
- `GET /api/admin/overview`
- `GET /api/stream`

## Production Notes

- Set a strong `JWT_SECRET`.
- Run behind HTTPS.
- Replace console-style notification placeholders with SMTP or a transactional email provider.
- For full image OCR, connect `extract_receipt_text` to Tesseract, AWS Textract, Azure Document Intelligence, or Google Document AI.
- For large-scale ML, persist training datasets and replace local heuristics with trained scikit-learn or gradient boosting models.
- Use PostgreSQL for concurrent multi-user production deployments.

## Structure

```text
app/
  config.py       Environment and currency settings
  database.py     SQLite connection, schema init, demo seeding
  main.py         FastAPI routes and application entry
  ml_engine.py    Classification, forecasting, anomaly, recommendation logic
  schemas.py      Pydantic request models
  security.py     Password hashing and JWT implementation
frontend/
  index.html      Single-page app shell
  styles.css      Responsive premium UI
  app.js          API client, charts, live updates, interactions
```
