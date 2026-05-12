# AI Smart Agriculture Monitoring and Crop Intelligence System

A complete Flask + Machine Learning smart agriculture platform with a modern interactive dashboard, real-time sensor simulation, crop intelligence APIs, disease image analysis, admin tools, PDF/CSV exports, login, voice chatbot support, and responsive glassmorphism UI.

## Features

- Real-time dashboard with animated counters, sensor cards, Chart.js analytics, notification center, map, and theme toggle
- Crop disease image upload with OpenCV feature extraction and ML classification
- Soil quality analysis with NPK scoring, fertility classification, fertilizer advice, and irrigation guidance
- AI crop recommendation engine using local ML models
- Smart irrigation controls with live moisture simulation and water-saving analytics
- Weather forecasting with optional OpenWeatherMap integration and offline intelligent fallback
- Farmer assistant chatbot with multilingual quick responses and browser voice input
- Market price prediction with trend charts and profit estimator
- Admin panel for farmers, crop records, reports, and system health
- Secure login, user profile, SQLite database
- Downloadable PDF report and CSV export
- ML training scripts and modular backend structure

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://127.0.0.1:5000`.

Default login:

- Email: `admin@agri.ai`
- Password: `admin123`

## Optional Weather API

The app works offline. To use live weather data, set an OpenWeatherMap API key:

```bash
set OPENWEATHER_API_KEY=your_key_here
python app.py
```

## Project Structure

```text
app.py
requirements.txt
agri_app/
  api/routes.py
  database.py
  ml/
    engine.py
    train_models.py
  services/
    weather.py
    reports.py
  static/
    css/styles.css
    js/app.js
  templates/
    login.html
    dashboard.html
data/
  app.db
models/
  *.joblib
```

## ML Notes

The runtime includes pure-Python prediction engines so it works even on Python 3.14 where compiled ML wheels may not be available. For a full scikit-learn/OpenCV/Pillow/TensorFlow environment, use Python 3.10-3.12 and install:

```bash
pip install -r requirements-ml-optional.txt
```

`agri_app/ml/train_models.py` and `agri_app/ml/train_cnn_disease.py` can be extended to train on Kaggle or field datasets.

For deep CNN disease detection, use `agri_app/ml/train_cnn_disease.py` as a TensorFlow training template with a directory dataset arranged by class.
