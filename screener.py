import json
import os
import math
from groq import Groq
from dotenv import load_dotenv
from models import ScreeningResponse

load_dotenv()

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a strict AI Technical Recruitment Screener.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 1 — PARSE THE JOB DESCRIPTION FIRST
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Extract every technical skill from the JD into two lists:
  • mandatory_skills_required — tagged "required", "must", "essential", or listed under core requirements
  • preferred_skills_required — tagged "nice to have", "preferred", "bonus", "plus", or optional

If the JD does not label them, treat ALL technical skills as mandatory.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 2 — MATCH EACH SKILL AGAINST RESUME
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For EVERY skill in mandatory_skills_required and preferred_skills_required:
  • Search the resume text for an EXPLICIT mention of that exact skill name.
  • A skill is matched ONLY if the exact tool/language/framework name appears in the resume.
  • Do NOT infer: knowing Python does not imply knowing Django. Knowing React does not imply knowing Vue.
  • Set found_in_resume = true only for explicit mentions.
  • Set context = the exact phrase or line from the resume that proves it (max 12 words), or "not found".

Populate skill_details as a flat list covering ALL mandatory + preferred skills.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 3 — COMPUTE TECHNICAL SCORE (0–100)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Let:
  M  = total mandatory skills  (minimum 1)
  Mm = mandatory skills matched (found_in_resume = true)
  P  = total preferred skills  (use 1 if none exist)
  Pm = preferred skills matched

  mandatory_pts = (Mm / M) * 32      ← max 32
  preferred_pts = (Pm / P) * 8       ← max 8
  raw = mandatory_pts + preferred_pts ← max 40

HARD CAPS (apply strictest that fits):
  Mm == 0              → raw = 0
  Mm < M * 0.50        → raw = min(raw, 18)
  Mm < M               → raw = min(raw, 28)

technical_skill_match.score = round(raw / 40 * 100)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 4 — EXPERIENCE SCORE (0–25 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Count only RELEVANT work experience (roles directly related to the JD).
Exclude unrelated jobs, pure academic projects, or personal hobbies.

  candidate_yrs >= required_yrs          → 25 pts, status = "Met"
  candidate_yrs >= required_yrs * 0.75   → 18 pts, status = "Nearly Met"
  candidate_yrs >= required_yrs * 0.50   → 12 pts, status = "Partial"
  candidate_yrs < required_yrs * 0.50    →  5 pts, status = "Not Met"
  no relevant experience                 →  0 pts, status = "No Experience"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 5 — PROJECTS SCORE (0–100 reported, raw 0–15 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Evaluate only projects EXPLICITLY listed in the resume. Score up to 3 projects:
  Project uses ≥1 mandatory skill                         → +3 pts
  Project uses multiple mandatory skills OR is complex    → additional +2 pts
  Project is unrelated to the role                        → 0 pts

  project_raw = sum, capped at 15
  projects_relevance_score = round(project_raw / 15 * 100)

No projects listed → 0.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 6 — EDUCATION (0–10 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Degree meets or exceeds JD requirement → 10, status = "Met"
  Related field, lower degree            →  6, status = "Partial"
  Unrelated field                        →  3, status = "Unrelated"
  No degree / not stated                 →  0, status = "Not Met"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 7 — CERTIFICATIONS (0–5 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  +2 pts each relevant cert, capped at 5. Irrelevant = 0.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 8 — SOFT SKILLS (0–5 pts)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  +1 pt per soft skill backed by concrete evidence (e.g. "led team of 6").
  Bare buzzwords ("good communicator") with no evidence = 0. Cap at 5.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STEP 9 — FINAL SCORE & DECISION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  overall = technical_raw_pts + exp_pts + project_raw_pts + edu_pts + cert_pts + soft_pts

  Penalties (cumulative, floor at 0):
    Mm == 0                         → overall = min(overall, 30)
    (M - Mm) / M > 0.60             → overall -= 10
    experience status = "No Experience" → overall -= 8

  Thresholds:
    overall >= 75 → recommendation = "Selected", eligible = true
    overall 55–74 → recommendation = "Consider",  eligible = true
    overall < 55  → recommendation = "Reject",    eligible = false

  confidence_score = overall / 100  (float 0.0–1.0)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
INTERVIEW QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Generate only for "Selected" or "Consider". Null for "Reject".
Each question MUST reference the candidate's actual skills/projects/companies from their resume.
Focus on mandatory skills the candidate claimed — probe depth.
Exactly 3 questions per category. expected_answer_hint = 1-line interviewer guide.

Respond with ONLY valid JSON — no extra text, no markdown fences:

{
  "candidate_name": "",
  "job_role": "",
  "overall_match_score": 0,
  "recommendation": "Selected",
  "eligible": true,
  "technical_skill_match": {
    "score": 0,
    "mandatory_skills_required": [],
    "preferred_skills_required": [],
    "matched_skills": [],
    "missing_skills": [],
    "skill_details": [
      {"skill": "", "found_in_resume": true, "context": ""}
    ]
  },
  "experience_analysis": {
    "required_years": "",
    "candidate_years": "",
    "status": "Met"
  },
  "education_analysis": {
    "degree": "",
    "status": "Met"
  },
  "certifications": [],
  "projects_relevance_score": 0,
  "strengths": [],
  "weaknesses": [],
  "final_decision": {
    "eligible": true,
    "confidence_score": 0.0,
    "reasoning": ""
  },
  "interview_questions": {
    "technical":  [{"category": "Technical",  "question": "", "expected_answer_hint": ""}],
    "experience": [{"category": "Experience", "question": "", "expected_answer_hint": ""}],
    "project":    [{"category": "Project",    "question": "", "expected_answer_hint": ""}],
    "behavioral": [{"category": "Behavioral", "question": "", "expected_answer_hint": ""}]
  },
  "github_analysis": {
    "url": null,
    "repositories_noted": [],
    "languages_inferred": [],
    "activity_summary": ""
  },
  "linkedin_analysis": {
    "url": null,
    "headline": "",
    "current_role": "",
    "total_experience": "",
    "companies_noted": [],
    "skills_listed": [],
    "profile_summary": ""
  }
}"""


def _recompute_scores(data: dict) -> dict:
    """
    Recompute technical score and overall score from the AI's own skill_details list.
    This prevents the AI from inflating scores — the numbers always match the evidence.
    """
    tsm = data.get("technical_skill_match", {})
    skill_details = tsm.get("skill_details", [])
    mandatory_required = tsm.get("mandatory_skills_required", [])
    preferred_required = tsm.get("preferred_skills_required", [])

    # Rebuild matched/missing from skill_details evidence
    matched, missing = [], []
    for sd in skill_details:
        skill = sd.get("skill", "")
        found = sd.get("found_in_resume", False)
        if found:
            matched.append(skill)
        else:
            missing.append(skill)

    # If AI didn't populate skill_details fall back to its own lists
    if not skill_details:
        matched = tsm.get("matched_skills", [])
        missing = tsm.get("missing_skills", [])
        mandatory_required = mandatory_required or matched + missing

    tsm["matched_skills"] = matched
    tsm["missing_skills"] = missing

    M  = max(len(mandatory_required), 1)
    P  = max(len(preferred_required), 1)
    Mm = sum(1 for s in matched if s in mandatory_required or not mandatory_required)
    Pm = sum(1 for s in matched if s in preferred_required)

    # If no explicit split, count all matched as mandatory
    if not mandatory_required:
        Mm = len(matched)
        M  = max(len(matched) + len(missing), 1)

    mandatory_pts = (Mm / M) * 32
    preferred_pts = (Pm / P) * 8
    raw = mandatory_pts + preferred_pts

    # Hard caps
    if Mm == 0:
        raw = 0
    elif Mm < M * 0.50:
        raw = min(raw, 18)
    elif Mm < M:
        raw = min(raw, 28)

    tech_score = round(raw / 40 * 100)
    tsm["score"] = tech_score
    data["technical_skill_match"] = tsm

    # Experience pts
    exp_status = data.get("experience_analysis", {}).get("status", "")
    exp_pts = {"Met": 25, "Exceeded": 25, "Nearly Met": 18, "Partial": 12,
               "Not Met": 5, "No Experience": 0}.get(exp_status, 5)

    # Projects pts (convert reported 0-100 back to raw /15)
    proj_score = data.get("projects_relevance_score", 0)
    proj_raw = round(proj_score / 100 * 15)

    # Education pts
    edu_status = data.get("education_analysis", {}).get("status", "")
    edu_pts = {"Met": 10, "Partial": 6, "Unrelated": 3, "Not Met": 0}.get(edu_status, 0)

    # Certs pts
    cert_pts = min(len(data.get("certifications", [])) * 2, 5)

    # Soft skills — keep AI's soft contribution capped; approximate from overall minus known components
    # Use AI overall as base for soft, but floor/cap it
    ai_overall = data.get("overall_match_score", 0)
    known_pts = raw + exp_pts + proj_raw + edu_pts + cert_pts
    soft_pts = max(0, min(5, ai_overall - known_pts))

    overall = math.floor(raw + exp_pts + proj_raw + edu_pts + cert_pts + soft_pts)

    # Penalties
    if Mm == 0:
        overall = min(overall, 30)
    if M > 0 and (M - Mm) / M > 0.60:
        overall -= 10
    if exp_status == "No Experience":
        overall -= 8
    overall = max(0, min(100, overall))

    data["overall_match_score"] = overall

    if overall >= 75:
        data["recommendation"] = "Selected"
        data["eligible"] = True
    elif overall >= 55:
        data["recommendation"] = "Consider"
        data["eligible"] = True
    else:
        data["recommendation"] = "Reject"
        data["eligible"] = False

    fd = data.setdefault("final_decision", {})
    fd["eligible"] = data["eligible"]
    fd["confidence_score"] = round(overall / 100, 2)

    return data


async def screen_candidate(resume_text: str, job_description: str, links: dict = None):
    links = links or {}
    github_url   = links.get("github")
    linkedin_url = links.get("linkedin")

    # Always instruct AI to populate profile analysis from resume content
    # regardless of whether URLs were found
    if github_url:
        gh_instruction = (
            f"GitHub Profile URL found: {github_url}\n"
            f"For github_analysis: set url='{github_url}', infer repositories_noted from "
            f"project/repo names in the resume, infer languages_inferred from skills/projects, "
            f"write a short activity_summary based on projects listed."
        )
    else:
        gh_instruction = (
            "No GitHub URL found in resume. For github_analysis: set url=null, "
            "but still infer repositories_noted from any project names mentioned, "
            "languages_inferred from skills listed, and write activity_summary from projects."
        )

    if linkedin_url:
        li_instruction = (
            f"LinkedIn Profile URL found: {linkedin_url}\n"
            f"For linkedin_analysis: set url='{linkedin_url}', infer headline, current_role, "
            f"total_experience, companies_noted, skills_listed, and profile_summary "
            f"from the candidate's work history, roles, and skills in the resume."
        )
    else:
        li_instruction = (
            "No LinkedIn URL found in resume. For linkedin_analysis: set url=null, "
            "but still infer headline, current_role, total_experience, companies_noted, "
            "skills_listed, and profile_summary from the resume content."
        )

    links_section = f"\nPROFILE ANALYSIS INSTRUCTIONS:\n{gh_instruction}\n{li_instruction}\n"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"RESUME:\n{resume_text}\n\n"
                    f"JOB DESCRIPTION:\n{job_description}\n"
                    f"{links_section}\n"
                    f"Screen this candidate strictly. Show skill_details for every skill. Return JSON only."
                ),
            },
        ],
    )

    raw_text = response.choices[0].message.content.strip()

    try:
        data = json.loads(raw_text)

        # Recompute scores from evidence — overrides AI numbers
        data = _recompute_scores(data)

        if data.get("recommendation", "").lower() == "reject":
            data["interview_questions"] = None

        # Force-set URLs — setdefault won't overwrite null set by AI
        gh = data.get("github_analysis")
        if not isinstance(gh, dict):
            gh = {}
        gh["url"] = github_url or gh.get("url")
        gh.setdefault("repositories_noted", [])
        gh.setdefault("languages_inferred", [])
        gh.setdefault("activity_summary", "")
        data["github_analysis"] = gh

        li = data.get("linkedin_analysis")
        if not isinstance(li, dict):
            li = {}
        li["url"] = linkedin_url or li.get("url")
        li.setdefault("headline", "")
        li.setdefault("current_role", "")
        li.setdefault("total_experience", "")
        li.setdefault("companies_noted", [])
        li.setdefault("skills_listed", [])
        li.setdefault("profile_summary", "")
        data["linkedin_analysis"] = li

        return ScreeningResponse(**data), raw_text
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        raise ValueError(raw_text) from exc
