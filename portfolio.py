import json
import os
import re
import httpx
from groq import Groq
from dotenv import load_dotenv
from models import PortfolioAnalysis

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a strict AI technical recruiter evaluating a candidate's portfolio against a specific job requirement.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — PARSE THE JOB REQUIREMENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extract all required and preferred technical skills, tools, frameworks, and languages from the job requirement text.
Separate into:
  • required_skills  — must-have skills
  • preferred_skills — nice-to-have skills

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — ANALYSE THE PORTFOLIO CONTENT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
From the portfolio URL, page content, and any metadata provided:
  • Identify every project, repository, or work sample
  • For each required/preferred skill, check if it appears EXPLICITLY in the portfolio content
  • Set found_in_portfolio = true ONLY if explicitly mentioned (repo name, code, README, tech stack)
  • Set evidence = the exact line/phrase where it was found, or "not found"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — REQUIREMENT MATCH SCORE (0–100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  R  = total required skills (min 1)
  Rm = required skills found in portfolio
  P  = total preferred skills (min 1)
  Pm = preferred skills found in portfolio

  req_pts  = (Rm / R) * 70    ← 70 pts max for required
  pref_pts = (Pm / P) * 30    ← 30 pts max for preferred
  requirement_match_score = round(req_pts + pref_pts)

Hard caps:
  Rm == 0              → requirement_match_score = max(score, 15)
  Rm < R * 0.50        → cap at 45
  Rm < R               → cap at 70

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — PORTFOLIO QUALITY SCORES (0–100 each)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  overall_quality_score  = weighted: 50% requirement_match + 20% tech_depth + 20% creativity + 10% consistency
  technical_depth_score  = complexity, architecture, variety of tech used in projects
  creativity_score       = originality, design, unique problem-solving
  consistency_score      = breadth of work, number of projects, regularity

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — RECOMMENDATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  overall_quality_score >= 75 → "Strong"
  overall_quality_score 55–74 → "Good"
  overall_quality_score 35–54 → "Average"
  overall_quality_score < 35  → "Weak"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — PROJECTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For each project found, include requirement_relevance explaining specifically how it maps to the job requirement.
If the project is unrelated, state that clearly.

Respond with ONLY valid JSON — no markdown fences, no extra text:

{
  "portfolio_url": "",
  "owner_name": "",
  "type": "GitHub",
  "summary": "",
  "job_role_targeted": "",
  "requirement_match_score": 0,
  "primary_languages": [],
  "frameworks_and_tools": [],
  "required_skills_found": [],
  "required_skills_missing": [],
  "skill_match_details": [
    {"skill": "", "required": true, "found_in_portfolio": true, "evidence": ""}
  ],
  "total_projects_noted": 0,
  "projects": [
    {
      "name": "",
      "description": "",
      "technologies": [],
      "highlights": [],
      "requirement_relevance": ""
    }
  ],
  "strengths": [],
  "areas_for_improvement": [],
  "overall_quality_score": 0,
  "creativity_score": 0,
  "technical_depth_score": 0,
  "consistency_score": 0,
  "recommendation": "Good",
  "hiring_verdict": ""
}"""


async def _github_bulk_check(username: str) -> tuple[bool, str]:
    """Fetch all public repos and detect if all were created within a 7-day window."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(
                f"https://api.github.com/users/{username}/repos",
                params={"per_page": 100, "sort": "created"},
                headers={"Accept": "application/vnd.github+json"},
            )
            if r.status_code != 200:
                return False, ""
            repos = r.json()
            if len(repos) < 2:
                return False, ""
            from datetime import datetime, timezone
            dates = sorted(
                datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
                for repo in repos
            )
            span_days = (dates[-1] - dates[0]).days
            if span_days <= 7:
                return True, (
                    f"All {len(repos)} repositories were created within {span_days} day(s) "
                    f"({dates[0].strftime('%Y-%m-%d')} – {dates[-1].strftime('%Y-%m-%d')}). "
                    "This pattern suggests bulk upload rather than organic development."
                )
    except Exception:
        pass
    return False, ""


def _detect_type(url: str) -> str:
    u = url.lower()
    if "github.com"   in u: return "GitHub"
    if "behance.net"  in u: return "Behance"
    if "dribbble.com" in u: return "Dribbble"
    if "linkedin.com" in u: return "LinkedIn"
    return "Personal Website"


def _github_meta(url: str) -> str:
    m = re.match(r"https?://github\.com/([^/?#]+)(?:/([^/?#]+))?", url, re.I)
    if not m:
        return ""
    user, repo = m.group(1), m.group(2)
    return f"GitHub repository: {user}/{repo}" if repo else f"GitHub profile: username={user}"


async def _fetch_page(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; PortfolioBot/1.0)"}
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as c:
            r = await c.get(url, headers=headers)
            if r.status_code == 200:
                text = re.sub(r"<[^>]+>", " ", r.text)
                text = re.sub(r"\s+", " ", text).strip()
                return text[:8000]
    except Exception:
        pass
    return ""


async def analyse_portfolio(url: str, job_requirements: str = "") -> PortfolioAnalysis:
    ptype        = _detect_type(url)
    gh_meta      = _github_meta(url) if ptype == "GitHub" else ""
    page_content = await _fetch_page(url)

    # Bulk upload detection for GitHub profiles
    bulk_detected, bulk_note = False, ""
    if ptype == "GitHub":
        m = re.match(r"https?://github\.com/([^/?#]+)/?$", url, re.I)
        if m:
            bulk_detected, bulk_note = await _github_bulk_check(m.group(1))

    parts = [
        f"PORTFOLIO URL: {url}",
        f"Portfolio type: {ptype}",
    ]
    if gh_meta:
        parts.append(gh_meta)
    if page_content:
        parts.append(f"PAGE CONTENT (truncated to 8 KB):\n{page_content}")
    else:
        parts.append("Note: page content could not be fetched — infer from URL structure and metadata only.")

    if job_requirements.strip():
        parts.append(f"JOB REQUIREMENT:\n{job_requirements.strip()}")
    else:
        parts.append(
            "No specific job requirement provided. "
            "Perform a general portfolio quality analysis. "
            "Set requirement_match_score = overall_quality_score. "
            "Mark all skills as required=false."
        )

    user_msg = "\n\n".join(parts) + "\n\nAnalyse this portfolio against the job requirement. Return JSON only."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg},
        ],
    )

    raw = response.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        data["portfolio_url"] = url
        data.setdefault("type", ptype)
        data.setdefault("skill_match_details", [])
        data.setdefault("required_skills_found",   [])
        data.setdefault("required_skills_missing", [])
        data.setdefault("job_role_targeted", "")
        data.setdefault("requirement_match_score", data.get("overall_quality_score", 0))
        # ensure every project has requirement_relevance
        for p in data.get("projects", []):
            p.setdefault("requirement_relevance", "")
        data["bulk_upload_detected"] = bulk_detected
        data["bulk_upload_note"]     = bulk_note
        return PortfolioAnalysis(**data)
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(raw) from exc
