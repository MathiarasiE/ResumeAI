from typing import Optional
from pydantic import BaseModel


class SkillDetail(BaseModel):
    skill: str
    found_in_resume: bool
    context: str          # exact phrase/line from resume proving it, or "not found"


class TechnicalSkillMatch(BaseModel):
    score: int
    mandatory_skills_required: list[str]
    preferred_skills_required: list[str]
    matched_skills: list[str]
    missing_skills: list[str]
    skill_details: list[SkillDetail]


class ExperienceAnalysis(BaseModel):
    required_years: str
    candidate_years: str
    status: str


class EducationAnalysis(BaseModel):
    degree: str
    status: str


class FinalDecision(BaseModel):
    eligible: bool
    confidence_score: float
    reasoning: str


class InterviewQuestion(BaseModel):
    category: str       # "Technical" | "Experience" | "Project" | "Behavioral"
    question: str
    expected_answer_hint: str


class InterviewQuestions(BaseModel):
    technical: list[InterviewQuestion]
    experience: list[InterviewQuestion]
    project: list[InterviewQuestion]
    behavioral: list[InterviewQuestion]


class PortfolioSkillMatch(BaseModel):
    skill: str
    required: bool          # was it in requirements
    found_in_portfolio: bool
    evidence: str           # where it was seen, or "not found"


class PortfolioProject(BaseModel):
    name: str
    description: str
    technologies: list[str]
    highlights: list[str]
    requirement_relevance: str   # how this project maps to the job requirement


class PortfolioAnalysis(BaseModel):
    portfolio_url: str
    owner_name: str
    type: str
    summary: str
    job_role_targeted: str           # role inferred from requirements
    requirement_match_score: int     # 0-100, how well portfolio meets the JR
    primary_languages: list[str]
    frameworks_and_tools: list[str]
    required_skills_found: list[str]
    required_skills_missing: list[str]
    skill_match_details: list[PortfolioSkillMatch]
    total_projects_noted: int
    projects: list[PortfolioProject]
    strengths: list[str]
    areas_for_improvement: list[str]
    overall_quality_score: int
    creativity_score: int
    technical_depth_score: int
    consistency_score: int
    recommendation: str              # "Strong", "Good", "Average", "Weak"
    hiring_verdict: str
    bulk_upload_detected: bool = False
    bulk_upload_note: str = ""


class GitHubAnalysis(BaseModel):
    url: Optional[str]
    repositories_noted: list[str]
    languages_inferred: list[str]
    activity_summary: str


class LinkedInAnalysis(BaseModel):
    url: Optional[str]
    headline: str
    current_role: str
    total_experience: str
    companies_noted: list[str]
    skills_listed: list[str]
    profile_summary: str


class ScreeningResponse(BaseModel):
    candidate_name: str
    job_role: str
    overall_match_score: int
    recommendation: str
    eligible: bool
    technical_skill_match: TechnicalSkillMatch
    experience_analysis: ExperienceAnalysis
    education_analysis: EducationAnalysis
    certifications: list[str]
    projects_relevance_score: int
    strengths: list[str]
    weaknesses: list[str]
    final_decision: FinalDecision
    interview_questions: Optional[InterviewQuestions] = None
    github_analysis: Optional[GitHubAnalysis] = None
    linkedin_analysis: Optional[LinkedInAnalysis] = None
