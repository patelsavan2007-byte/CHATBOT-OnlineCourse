"""Pydantic schemas for SkillForge AI structured outputs.

These models define the data contracts between:
- Gemini structured output responses
- Internal pipeline components
- API responses to the frontend

Every Gemini response is validated against these schemas before
being returned to the frontend.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProfileSource(str, Enum):
    """Where the student data came from."""
    RESUME = "resume"
    PORTFOLIO = "portfolio"
    BOTH = "both"


class Difficulty(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# ---------------------------------------------------------------------------
# Student Profile
# ---------------------------------------------------------------------------

class ProjectDetail(BaseModel):
    """A single project extracted from resume or portfolio."""
    name: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)
    url: Optional[str] = None
    source: Optional[str] = None  # "resume", "portfolio", "github"


class EducationDetail(BaseModel):
    institution: str = ""
    degree: str = ""
    field: str = ""
    year: Optional[str] = None
    gpa: Optional[str] = None


class ExperienceDetail(BaseModel):
    company: str = ""
    role: str = ""
    duration: str = ""
    description: str = ""
    technologies: List[str] = Field(default_factory=list)


class CertificationDetail(BaseModel):
    name: str = ""
    issuer: str = ""
    year: Optional[str] = None
    url: Optional[str] = None


class StudentProfile(BaseModel):
    """Unified student profile extracted from resume and/or portfolio."""
    skills: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)
    projects: List[ProjectDetail] = Field(default_factory=list)
    education: List[EducationDetail] = Field(default_factory=list)
    experience: List[ExperienceDetail] = Field(default_factory=list)
    certifications: List[CertificationDetail] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    links: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    summary: str = ""
    source: ProfileSource = ProfileSource.RESUME
    confidence: str = "high"  # high, medium, low
    extraction_notes: str = ""


# ---------------------------------------------------------------------------
# Skill Gap Analysis
# ---------------------------------------------------------------------------

class SkillGapAnalysis(BaseModel):
    """Comparison of student profile against target role requirements."""
    career_readiness_score: int = Field(default=0, ge=0, le=100)
    strong_skills: List[str] = Field(default_factory=list)
    developing_skills: List[str] = Field(default_factory=list)
    critical_gaps: List[str] = Field(default_factory=list)
    missing_technologies: List[str] = Field(default_factory=list)
    missing_project_experience: List[str] = Field(default_factory=list)
    analysis_summary: str = ""


# ---------------------------------------------------------------------------
# Learning Roadmap
# ---------------------------------------------------------------------------

class RoadmapStep(BaseModel):
    """A single step in the personalized learning roadmap."""
    order: int = 0
    topic: str = ""
    reason: str = ""  # Why this step for THIS student
    skills: List[str] = Field(default_factory=list)
    estimated_duration: str = ""
    difficulty: Difficulty = Difficulty.BEGINNER
    prerequisites: List[str] = Field(default_factory=list)
    recommended_project: str = ""
    recommended_resource: str = ""


class LearningRoadmap(BaseModel):
    """Personalized learning roadmap."""
    target_role: str = ""
    steps: List[RoadmapStep] = Field(default_factory=list)
    total_estimated_duration: str = ""
    approach_summary: str = ""


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

class CourseRecommendation(BaseModel):
    title: str = ""
    platform: str = ""
    relevant_skill: str = ""
    why_recommended: str = ""  # Why for THIS student
    difficulty: Difficulty = Difficulty.BEGINNER
    estimated_time: str = ""
    url: Optional[str] = None
    is_free: Optional[bool] = None


class ProjectRecommendation(BaseModel):
    title: str = ""
    description: str = ""
    relevant_skill: str = ""
    why_recommended: str = ""
    difficulty: Difficulty = Difficulty.BEGINNER
    estimated_time: str = ""
    technologies: List[str] = Field(default_factory=list)
    learning_outcomes: List[str] = Field(default_factory=list)


class CertificationRecommendation(BaseModel):
    title: str = ""
    issuer: str = ""
    relevant_skill: str = ""
    why_recommended: str = ""
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    estimated_time: str = ""
    url: Optional[str] = None
    cost: Optional[str] = None


class InterviewQuestion(BaseModel):
    question: str = ""
    topic: str = ""
    difficulty: Difficulty = Difficulty.INTERMEDIATE
    tip: str = ""


class InterviewPreparation(BaseModel):
    target_role: str = ""
    focus_areas: List[str] = Field(default_factory=list)
    questions: List[InterviewQuestion] = Field(default_factory=list)
    general_tips: List[str] = Field(default_factory=list)
    why_these_areas: str = ""  # Why these focus areas for THIS student


class CareerAdvice(BaseModel):
    title: str = ""
    advice: str = ""
    relevant_to: str = ""
    priority: str = "medium"  # high, medium, low
    action_items: List[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Final Career Plan (unified container)
# ---------------------------------------------------------------------------

class FinalCareerPlan(BaseModel):
    """Complete personalized career plan — the main output of SkillForge AI."""
    student_profile: StudentProfile = Field(default_factory=StudentProfile)
    skill_gap: SkillGapAnalysis = Field(default_factory=SkillGapAnalysis)
    roadmap: LearningRoadmap = Field(default_factory=LearningRoadmap)
    courses: List[CourseRecommendation] = Field(default_factory=list)
    projects: List[ProjectRecommendation] = Field(default_factory=list)
    certifications: List[CertificationRecommendation] = Field(default_factory=list)
    interview_prep: InterviewPreparation = Field(default_factory=InterviewPreparation)
    career_advice: List[CareerAdvice] = Field(default_factory=list)
    target_role: str = ""
    generated_at: str = ""
    input_mode: str = ""  # "resume_only", "portfolio_only", "both"


# ---------------------------------------------------------------------------
# API Request / Response models
# ---------------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """Request body for career analysis endpoint."""
    target_career: str = Field(..., min_length=1, description="Target career/role")
    portfolio_url: Optional[str] = Field(default=None, description="Portfolio or GitHub URL")
    user_id: Optional[str] = Field(default=None, description="Client-generated user ID")


class AnalysisResponse(BaseModel):
    """Response from the analysis endpoint."""
    analysis_id: str = ""
    user_id: str = ""
    student_profile: StudentProfile = Field(default_factory=StudentProfile)
    skill_gap: SkillGapAnalysis = Field(default_factory=SkillGapAnalysis)
    target_role: str = ""
    input_mode: str = ""
    created_at: str = ""


class PlanResponse(BaseModel):
    """Response from the plan generation endpoint."""
    plan_id: str = ""
    user_id: str = ""
    career_plan: FinalCareerPlan = Field(default_factory=FinalCareerPlan)
    created_at: str = ""
