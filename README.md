# ResumeAI

ResumeAI is a FastAPI-based resume screening and portfolio analysis app. It uses Groq-hosted LLaMA models to score resumes against job descriptions, evaluate portfolios, and return structured recommendations through both API endpoints and a simple static frontend.

## Features

- Resume screening with an AI verdict and detailed skill matching
- Portfolio analysis for GitHub profiles, repositories, and personal sites
- Static frontend pages for home, screening, dashboard, login, and portfolio analysis
- Authentication using a simple token-based login flow
- Support for PDF, DOCX, and TXT resume uploads

## Requirements

- Python 3.9+
- A Groq API key

## Setup

1. Create a virtual environment and install dependencies:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

2. Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
APP_USERNAME=admin
APP_PASSWORD=admin123
HOST=127.0.0.1
PORT=8000
```

`APP_USERNAME` and `APP_PASSWORD` are optional. If omitted, the app defaults to `admin` and `admin123`.

## Run

Start the app with:

```bash
python main.py
```

The app will be available at `http://127.0.0.1:8000` by default.

## Main Pages

- `/` - Home
- `/screen` - Resume screening
- `/dashboard` - Candidate dashboard
- `/portfolio` - Portfolio analysis
- `/login` - Login page
- `/about` - Product overview

## API Endpoints

- `POST /api/login`
- `POST /api/logout`
- `GET /api/verify`
- `POST /screen`
- `POST /api/portfolio`
- `GET /health`

## Project Structure

- `main.py` - FastAPI app and routes
- `auth.py` - Simple token authentication helpers
- `parser.py` - Resume text extraction utilities
- `screener.py` - Resume scoring and screening logic
- `portfolio.py` - Portfolio analysis logic
- `models.py` - Pydantic response models
- `static/` - Frontend pages and assets

## Notes

- The app loads environment variables from `.env` at startup.
- Login tokens are stored in memory, so they reset when the app restarts.
- The repo is designed for local development and demo use unless you add production-grade auth and persistence.