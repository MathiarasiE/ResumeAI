import os
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, UploadFile, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional

from models import ScreeningResponse, PortfolioAnalysis
from screener import screen_candidate
from portfolio import analyse_portfolio
from parser import extract_text
import auth

load_dotenv()

app = FastAPI(title="Resume Screening API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# ── Pages ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=FileResponse)
async def home():
    return FileResponse("static/index.html")

@app.get("/screen", response_class=FileResponse)
async def screen_page():
    return FileResponse("static/screen.html")

@app.get("/about", response_class=FileResponse)
async def about_page():
    return FileResponse("static/about.html")

@app.get("/dashboard", response_class=FileResponse)
async def dashboard_page():
    return FileResponse("static/dashboard.html")

@app.get("/portfolio", response_class=FileResponse)
async def portfolio_page():
    return FileResponse("static/portfolio.html")

@app.get("/login", response_class=FileResponse)
async def login_page():
    return FileResponse("static/login.html")


# ── Auth endpoints ──────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/login")
async def api_login(body: LoginRequest):
    token = auth.login(body.username, body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid username or password.")
    return {"token": token}

@app.post("/api/logout")
async def api_logout(authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    if token:
        auth.logout(token)
    return {"status": "logged out"}

@app.get("/api/verify")
async def api_verify(authorization: Optional[str] = Header(None)):
    token = _extract_token(authorization)
    if not token or not auth.verify(token):
        raise HTTPException(status_code=401, detail="Not authenticated.")
    return {"status": "ok"}


# ── Portfolio endpoint ─────────────────────────────────────────────────────────

class PortfolioRequest(BaseModel):
    url: str
    job_requirements: str = ""

@app.post("/api/portfolio", response_model=PortfolioAnalysis)
async def api_portfolio(
    body: PortfolioRequest,
    authorization: Optional[str] = Header(None),
):
    token = _extract_token(authorization)
    if not token or not auth.verify(token):
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")
    url = body.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Portfolio URL is required.")
    try:
        result = await analyse_portfolio(url, body.job_requirements)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail={"error": "AI returned invalid JSON", "raw_response": str(exc)})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Screening endpoint ──────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/screen", response_model=ScreeningResponse)
async def screen(
    resume: UploadFile = File(...),
    job_description: str = Form(...),
    authorization: Optional[str] = Header(None),
):
    token = _extract_token(authorization)
    if not token or not auth.verify(token):
        raise HTTPException(status_code=401, detail="Not authenticated. Please log in.")

    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured.")

    resume_text = await extract_text(resume)
    from parser import extract_links
    links = extract_links(resume_text)

    if len(resume_text.strip()) < 50:
        raise HTTPException(status_code=400, detail="Resume appears empty or too short.")
    if len(job_description.strip()) < 20:
        raise HTTPException(status_code=400, detail="Job description is too short.")

    try:
        result, _ = await screen_candidate(resume_text, job_description, links)
        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error": "AI returned invalid JSON", "raw_response": str(exc)},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _extract_token(authorization: Optional[str]) -> Optional[str]:
    if authorization and authorization.startswith("Bearer "):
        return authorization[7:]
    return None


if __name__ == "__main__":
    # Allow running the app with: `python main.py`
    # Use environment variables `HOST` and `PORT` if provided.
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
