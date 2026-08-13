"""Career engine — core AI pipeline orchestrator for SkillForge AI.

Responsibilities:
1. Profile merging (resume + portfolio based on input mode)
2. Target role requirements catalog
3. Skill gap calculation
4. Gemini-powered personalized plan generation
5. Recommendation generation with web-search grounding

The engine NEVER reuses previous analysis data from a different input mode.
Each request is analyzed fresh based on the CURRENT inputs only.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.gemini_client import get_gemini_client
from app.schemas import (
    CareerAdvice,
    CertificationRecommendation,
    CourseRecommendation,
    Difficulty,
    FinalCareerPlan,
    InterviewPreparation,
    InterviewQuestion,
    LearningRoadmap,
    ProfileSource,
    ProjectRecommendation,
    RoadmapStep,
    SkillGapAnalysis,
    StudentProfile,
)
from app.utils import logger, print_info

# ---------------------------------------------------------------------------
# Target Role Requirements Catalog
# ---------------------------------------------------------------------------

ROLE_REQUIREMENTS: Dict[str, Dict] = {
    "Full Stack Developer": {
        "required_skills": [
            "HTML", "CSS", "JavaScript", "React or Angular or Vue",
            "Node.js or Python or Java", "REST APIs", "SQL", "Git",
            "Database Design", "Authentication",
        ],
        "nice_to_have": [
            "TypeScript", "Docker", "CI/CD", "Cloud (AWS/GCP/Azure)",
            "GraphQL", "Redis", "Testing", "System Design",
        ],
        "typical_projects": [
            "Full-stack web application", "E-commerce platform",
            "Real-time chat application", "Dashboard with analytics",
        ],
    },
    "Frontend Developer": {
        "required_skills": [
            "HTML", "CSS", "JavaScript", "React or Angular or Vue",
            "Responsive Design", "Git", "REST APIs", "Web Performance",
        ],
        "nice_to_have": [
            "TypeScript", "Next.js", "Testing (Jest/Cypress)", "Figma",
            "Accessibility (a11y)", "CSS-in-JS", "State Management",
            "PWA", "Web Animations",
        ],
        "typical_projects": [
            "Single Page Application", "Component Library",
            "Progressive Web App", "Portfolio Website",
        ],
    },
    "Backend Developer": {
        "required_skills": [
            "Python or Java or Go or C#", "REST APIs", "SQL",
            "Database Design", "Authentication & Authorization",
            "Git", "Linux Basics", "Data Structures & Algorithms",
        ],
        "nice_to_have": [
            "Docker", "Kubernetes", "Message Queues", "Caching (Redis)",
            "GraphQL", "Microservices", "CI/CD", "Cloud Services",
            "System Design", "gRPC",
        ],
        "typical_projects": [
            "REST API service", "Microservices architecture",
            "Database migration tool", "API Gateway",
        ],
    },
    "Data Scientist": {
        "required_skills": [
            "Python", "Pandas", "NumPy", "Statistics",
            "Machine Learning", "Data Visualization", "SQL",
            "Scikit-learn", "Jupyter Notebooks",
        ],
        "nice_to_have": [
            "Deep Learning (TensorFlow/PyTorch)", "NLP", "Computer Vision",
            "Big Data (Spark)", "Cloud ML Services", "A/B Testing",
            "Feature Engineering", "MLOps", "R",
        ],
        "typical_projects": [
            "Predictive model", "Data analysis pipeline",
            "Recommendation system", "NLP text classifier",
        ],
    },
    "ML Engineer": {
        "required_skills": [
            "Python", "Machine Learning", "Deep Learning",
            "TensorFlow or PyTorch", "Data Processing",
            "Model Evaluation", "Git", "Linux",
        ],
        "nice_to_have": [
            "MLOps", "Docker", "Kubernetes", "Model Deployment",
            "Feature Store", "Experiment Tracking (MLflow/W&B)",
            "Distributed Training", "Cloud ML Platforms",
        ],
        "typical_projects": [
            "End-to-end ML pipeline", "Model serving API",
            "Computer vision application", "NLP system",
        ],
    },
    "DevOps Engineer": {
        "required_skills": [
            "Linux", "Docker", "CI/CD", "Git", "Bash/Shell Scripting",
            "Cloud (AWS/GCP/Azure)", "Networking Basics",
            "Monitoring & Logging",
        ],
        "nice_to_have": [
            "Kubernetes", "Terraform", "Ansible", "Prometheus/Grafana",
            "Security Best Practices", "Service Mesh", "GitOps",
            "Serverless", "Database Administration",
        ],
        "typical_projects": [
            "CI/CD pipeline", "Infrastructure as Code setup",
            "Monitoring dashboard", "Container orchestration",
        ],
    },
    "Mobile Developer": {
        "required_skills": [
            "React Native or Flutter or Swift or Kotlin",
            "Mobile UI Design", "REST APIs", "Git",
            "App Store Deployment", "State Management",
        ],
        "nice_to_have": [
            "Firebase", "Push Notifications", "Offline Storage",
            "Mobile Testing", "CI/CD for Mobile", "Performance Optimization",
            "Native Modules", "Cross-platform Development",
        ],
        "typical_projects": [
            "Cross-platform mobile app", "Social media app",
            "E-commerce mobile app", "Location-based app",
        ],
    },
    "Cloud Architect": {
        "required_skills": [
            "AWS or GCP or Azure", "Networking", "Security",
            "Infrastructure as Code", "Distributed Systems",
            "Cost Optimization", "High Availability Design",
        ],
        "nice_to_have": [
            "Multi-cloud Strategy", "Compliance Frameworks",
            "Serverless Architecture", "Service Mesh",
            "Data Architecture", "Migration Planning",
        ],
        "typical_projects": [
            "Cloud migration plan", "Multi-region architecture",
            "Serverless application", "Disaster recovery setup",
        ],
    },
    "Cybersecurity Analyst": {
        "required_skills": [
            "Networking", "Linux", "Security Fundamentals",
            "Threat Analysis", "Incident Response",
            "Firewalls & IDS/IPS", "SIEM Tools",
        ],
        "nice_to_have": [
            "Penetration Testing", "Cryptography", "Cloud Security",
            "Forensics", "Compliance (SOC2/GDPR)", "Python Scripting",
            "Vulnerability Assessment", "Zero Trust Architecture",
        ],
        "typical_projects": [
            "Security audit report", "Penetration test",
            "Incident response playbook", "Security automation script",
        ],
    },
    "UI/UX Designer": {
        "required_skills": [
            "Figma or Sketch", "User Research", "Wireframing",
            "Prototyping", "Design Systems", "Usability Testing",
            "Visual Design", "Responsive Design",
        ],
        "nice_to_have": [
            "HTML/CSS", "Animation Design", "Accessibility",
            "Design Thinking", "Information Architecture",
            "A/B Testing", "Design Handoff Tools",
        ],
        "typical_projects": [
            "Mobile app redesign", "Design system creation",
            "User research study", "Interactive prototype",
        ],
    },
}


def get_available_roles() -> List[str]:
    """Return the list of supported target roles."""
    return sorted(ROLE_REQUIREMENTS.keys())


def merge_profiles(
    resume_profile: Optional[StudentProfile],
    portfolio_profile: Optional[StudentProfile],
) -> StudentProfile:
    """Merge resume and portfolio profiles into a unified profile.

    Rules:
    - Resume only → resume profile as-is
    - Portfolio only → portfolio profile as-is
    - Both → intelligent merge (union of skills, projects, etc.)
    - NEVER automatically use one when only the other is provided
    """
    if resume_profile and portfolio_profile:
        # Merge both
        merged_skills = list(dict.fromkeys(
            resume_profile.skills + portfolio_profile.skills
        ))
        merged_tech = list(dict.fromkeys(
            resume_profile.technologies + portfolio_profile.technologies
        ))
        merged_projects = resume_profile.projects + portfolio_profile.projects
        merged_education = resume_profile.education + portfolio_profile.education
        merged_experience = resume_profile.experience + portfolio_profile.experience
        merged_certs = resume_profile.certifications + portfolio_profile.certifications
        merged_achievements = list(dict.fromkeys(
            resume_profile.achievements + portfolio_profile.achievements
        ))
        merged_links = list(dict.fromkeys(
            resume_profile.links + portfolio_profile.links
        ))
        merged_strengths = list(dict.fromkeys(
            resume_profile.strengths + portfolio_profile.strengths
        ))

        summary_parts = []
        if resume_profile.summary:
            summary_parts.append(f"Resume: {resume_profile.summary}")
        if portfolio_profile.summary:
            summary_parts.append(f"Portfolio: {portfolio_profile.summary}")

        return StudentProfile(
            skills=merged_skills,
            technologies=merged_tech,
            projects=merged_projects,
            education=merged_education,
            experience=merged_experience,
            certifications=merged_certs,
            achievements=merged_achievements,
            links=merged_links,
            strengths=merged_strengths,
            summary=" | ".join(summary_parts),
            source=ProfileSource.BOTH,
            confidence="high" if (resume_profile.confidence == "high" or portfolio_profile.confidence == "high") else "medium",
        )
    elif resume_profile:
        return resume_profile
    elif portfolio_profile:
        return portfolio_profile
    else:
        return StudentProfile(
            source=ProfileSource.RESUME,
            confidence="low",
            extraction_notes="No resume or portfolio data available.",
        )


def calculate_skill_gap(
    profile: StudentProfile,
    target_role: str,
) -> SkillGapAnalysis:
    """Compare student profile against target role requirements.

    Returns structured skill gap analysis with readiness score.
    """
    role_reqs = ROLE_REQUIREMENTS.get(target_role)
    if not role_reqs:
        # Use Gemini to determine requirements for custom role
        return _gemini_skill_gap(profile, target_role)

    required = role_reqs["required_skills"]
    nice_to_have = role_reqs["nice_to_have"]
    typical_projects = role_reqs["typical_projects"]

    student_skills_lower = {s.lower() for s in profile.skills + profile.technologies}
    student_project_tech = set()
    for proj in profile.projects:
        for t in proj.technologies:
            student_project_tech.add(t.lower())
    student_skills_lower.update(student_project_tech)

    # Categorize skills
    strong = []
    developing = []
    critical_gaps = []
    missing_tech = []

    for skill in required:
        # Handle "X or Y or Z" format
        alternatives = [s.strip() for s in skill.split(" or ")]
        matched = any(
            alt.lower() in student_skills_lower or
            any(alt.lower() in s for s in student_skills_lower)
            for alt in alternatives
        )
        if matched:
            strong.append(skill)
        else:
            critical_gaps.append(skill)

    for skill in nice_to_have:
        alternatives = [s.strip() for s in skill.split(" or ")]
        matched = any(
            alt.lower() in student_skills_lower or
            any(alt.lower() in s for s in student_skills_lower)
            for alt in alternatives
        )
        if matched:
            developing.append(skill)
        else:
            missing_tech.append(skill)

    # Calculate readiness score
    total_required = len(required)
    matched_required = len(strong)
    total_nice = len(nice_to_have)
    matched_nice = len(developing)

    if total_required > 0:
        required_score = (matched_required / total_required) * 70  # 70% weight
    else:
        required_score = 35

    if total_nice > 0:
        nice_score = (matched_nice / total_nice) * 30  # 30% weight
    else:
        nice_score = 15

    readiness_score = min(100, int(required_score + nice_score))

    # Missing project experience
    missing_projects = []
    student_project_names = " ".join(
        (p.name + " " + p.description).lower() for p in profile.projects
    )
    for proj_type in typical_projects:
        if not any(
            keyword in student_project_names
            for keyword in proj_type.lower().split()
            if len(keyword) > 3
        ):
            missing_projects.append(proj_type)

    summary = (
        f"Career readiness for {target_role}: {readiness_score}%. "
        f"{len(strong)} strong skills, {len(critical_gaps)} critical gaps. "
        f"Focus areas: {', '.join(critical_gaps[:3]) if critical_gaps else 'refine existing skills'}."
    )

    return SkillGapAnalysis(
        career_readiness_score=readiness_score,
        strong_skills=strong,
        developing_skills=developing,
        critical_gaps=critical_gaps,
        missing_technologies=missing_tech,
        missing_project_experience=missing_projects,
        analysis_summary=summary,
    )


def _gemini_skill_gap(
    profile: StudentProfile,
    target_role: str,
) -> SkillGapAnalysis:
    """Use Gemini to analyze skill gaps for roles not in the catalog."""
    client = get_gemini_client()
    if not client.is_available:
        return SkillGapAnalysis(
            analysis_summary=f"Unable to analyze skill gap for '{target_role}' (Gemini unavailable).",
        )

    prompt = f"""Analyze the skill gap between this student and the target role.

Student Skills: {', '.join(profile.skills[:30])}
Student Technologies: {', '.join(profile.technologies[:30])}
Student Projects: {', '.join(p.name for p in profile.projects[:10])}
Student Experience: {', '.join(e.role + ' at ' + e.company for e in profile.experience[:5])}
Target Role: {target_role}

Return JSON:
{{
  "career_readiness_score": <0-100>,
  "strong_skills": ["skills the student has that match the role"],
  "developing_skills": ["skills the student has partially"],
  "critical_gaps": ["required skills the student is missing"],
  "missing_technologies": ["nice-to-have technologies missing"],
  "missing_project_experience": ["types of projects they should build"],
  "analysis_summary": "2-3 sentence summary"
}}"""

    result = client.generate_json(prompt, response_model=SkillGapAnalysis, temperature=0.2)
    if result:
        try:
            return SkillGapAnalysis.model_validate(result)
        except Exception:
            pass

    return SkillGapAnalysis(
        analysis_summary=f"Could not complete skill gap analysis for '{target_role}'.",
    )


def generate_personalized_plan(
    profile: StudentProfile,
    skill_gap: SkillGapAnalysis,
    target_role: str,
    input_mode: str,
) -> FinalCareerPlan:
    """Generate a complete personalized career plan using Gemini.

    This is the main orchestrator that produces:
    - Learning roadmap
    - Course recommendations
    - Project recommendations
    - Certification recommendations
    - Interview preparation
    - Career advice

    Each recommendation explains WHY it was selected for THIS student.
    """
    client = get_gemini_client()

    if not client.is_available:
        return _fallback_plan(profile, skill_gap, target_role, input_mode)

    # Build the comprehensive prompt
    prompt = _build_plan_prompt(profile, skill_gap, target_role)

    result = client.generate_json(prompt, temperature=0.4, max_tokens=8192)

    if result is None:
        logger.warning("Gemini plan generation returned None, using fallback")
        return _fallback_plan(profile, skill_gap, target_role, input_mode)

    # Parse and validate each section
    plan = _parse_plan_response(result, profile, skill_gap, target_role, input_mode)
    return plan


def _build_plan_prompt(
    profile: StudentProfile,
    skill_gap: SkillGapAnalysis,
    target_role: str,
) -> str:
    """Build the comprehensive Gemini prompt for plan generation."""

    projects_desc = "\n".join(
        f"  - {p.name}: {p.description} ({', '.join(p.technologies)})"
        for p in profile.projects[:10]
    ) or "  None"

    education_desc = "\n".join(
        f"  - {e.degree} in {e.field} from {e.institution} ({e.year or 'N/A'})"
        for e in profile.education[:5]
    ) or "  None"

    experience_desc = "\n".join(
        f"  - {e.role} at {e.company} ({e.duration}): {e.description[:100]}"
        for e in profile.experience[:5]
    ) or "  None"

    return f"""You are an expert AI career mentor. Create a PERSONALIZED career plan for this specific student.

=== STUDENT PROFILE ===
Skills: {', '.join(profile.skills[:25]) or 'None identified'}
Technologies: {', '.join(profile.technologies[:25]) or 'None identified'}
Projects:
{projects_desc}
Education:
{education_desc}
Experience:
{experience_desc}
Certifications: {', '.join(c.name for c in profile.certifications[:5]) or 'None'}
Strengths: {', '.join(profile.strengths[:10]) or 'Not yet identified'}

=== SKILL GAP ANALYSIS ===
Career Readiness: {skill_gap.career_readiness_score}%
Strong Skills: {', '.join(skill_gap.strong_skills[:10]) or 'None'}
Developing Skills: {', '.join(skill_gap.developing_skills[:10]) or 'None'}
Critical Gaps: {', '.join(skill_gap.critical_gaps[:10]) or 'None'}
Missing Technologies: {', '.join(skill_gap.missing_technologies[:10]) or 'None'}

=== TARGET ROLE ===
{target_role}

=== INSTRUCTIONS ===
Create a PERSONALIZED plan. Every recommendation must explain WHY it's recommended for THIS specific student based on their current skills, gaps, and projects.

DO NOT give generic advice. Reference the student's actual skills and gaps.

For courses and certifications, recommend REAL platforms and resources (Coursera, Udemy, freeCodeCamp, edX, Google, AWS, etc.). 
If you know a specific course URL, include it. If not, omit the URL field rather than inventing one.

Return JSON:
{{
  "roadmap": {{
    "target_role": "{target_role}",
    "steps": [
      {{
        "order": 1,
        "topic": "what to learn",
        "reason": "WHY this student specifically needs this, referencing their current skills/gaps",
        "skills": ["skills gained"],
        "estimated_duration": "e.g., 2-3 weeks",
        "difficulty": "beginner/intermediate/advanced",
        "prerequisites": ["what they need first"],
        "recommended_project": "a specific project to practice",
        "recommended_resource": "specific course or resource name"
      }}
    ],
    "total_estimated_duration": "e.g., 4-6 months",
    "approach_summary": "Overall learning strategy for this student"
  }},
  "courses": [
    {{
      "title": "specific course name",
      "platform": "platform name",
      "relevant_skill": "skill this covers",
      "why_recommended": "WHY for THIS student",
      "difficulty": "beginner/intermediate/advanced",
      "estimated_time": "e.g., 20 hours",
      "url": "URL if known, null if not",
      "is_free": true/false
    }}
  ],
  "projects": [
    {{
      "title": "project name",
      "description": "what to build",
      "relevant_skill": "skill practiced",
      "why_recommended": "WHY for THIS student",
      "difficulty": "beginner/intermediate/advanced",
      "estimated_time": "e.g., 2 weeks",
      "technologies": ["tech to use"],
      "learning_outcomes": ["what they'll learn"]
    }}
  ],
  "certifications": [
    {{
      "title": "certification name",
      "issuer": "issuing body",
      "relevant_skill": "skill validated",
      "why_recommended": "WHY for THIS student",
      "difficulty": "beginner/intermediate/advanced",
      "estimated_time": "preparation time",
      "url": "URL if known, null if not",
      "cost": "approximate cost"
    }}
  ],
  "interview_prep": {{
    "target_role": "{target_role}",
    "focus_areas": ["areas to focus on"],
    "questions": [
      {{
        "question": "interview question",
        "topic": "topic area",
        "difficulty": "beginner/intermediate/advanced",
        "tip": "how to approach this"
      }}
    ],
    "general_tips": ["tips for this student"],
    "why_these_areas": "WHY these focus areas for THIS student"
  }},
  "career_advice": [
    {{
      "title": "advice title",
      "advice": "detailed advice",
      "relevant_to": "what aspect of their career",
      "priority": "high/medium/low",
      "action_items": ["specific actions to take"]
    }}
  ]
}}"""


def _parse_plan_response(
    result: dict,
    profile: StudentProfile,
    skill_gap: SkillGapAnalysis,
    target_role: str,
    input_mode: str,
) -> FinalCareerPlan:
    """Parse Gemini response into a validated FinalCareerPlan."""

    # Parse roadmap
    roadmap_data = result.get("roadmap", {})
    roadmap_steps = []
    for step in roadmap_data.get("steps", []):
        try:
            roadmap_steps.append(RoadmapStep(
                order=step.get("order", 0),
                topic=step.get("topic", ""),
                reason=step.get("reason", ""),
                skills=step.get("skills", []),
                estimated_duration=step.get("estimated_duration", ""),
                difficulty=_parse_difficulty(step.get("difficulty", "beginner")),
                prerequisites=step.get("prerequisites", []),
                recommended_project=step.get("recommended_project", ""),
                recommended_resource=step.get("recommended_resource", ""),
            ))
        except Exception as exc:
            logger.warning("Failed to parse roadmap step: %s", exc)

    roadmap = LearningRoadmap(
        target_role=target_role,
        steps=roadmap_steps,
        total_estimated_duration=roadmap_data.get("total_estimated_duration", ""),
        approach_summary=roadmap_data.get("approach_summary", ""),
    )

    # Parse courses
    courses = []
    for c in result.get("courses", []):
        try:
            courses.append(CourseRecommendation(
                title=c.get("title", ""),
                platform=c.get("platform", ""),
                relevant_skill=c.get("relevant_skill", ""),
                why_recommended=c.get("why_recommended", ""),
                difficulty=_parse_difficulty(c.get("difficulty", "beginner")),
                estimated_time=c.get("estimated_time", ""),
                url=c.get("url"),
                is_free=c.get("is_free"),
            ))
        except Exception as exc:
            logger.warning("Failed to parse course: %s", exc)

    # Parse projects
    projects = []
    for p in result.get("projects", []):
        try:
            projects.append(ProjectRecommendation(
                title=p.get("title", ""),
                description=p.get("description", ""),
                relevant_skill=p.get("relevant_skill", ""),
                why_recommended=p.get("why_recommended", ""),
                difficulty=_parse_difficulty(p.get("difficulty", "beginner")),
                estimated_time=p.get("estimated_time", ""),
                technologies=p.get("technologies", []),
                learning_outcomes=p.get("learning_outcomes", []),
            ))
        except Exception as exc:
            logger.warning("Failed to parse project: %s", exc)

    # Parse certifications
    certs = []
    for cert in result.get("certifications", []):
        try:
            certs.append(CertificationRecommendation(
                title=cert.get("title", ""),
                issuer=cert.get("issuer", ""),
                relevant_skill=cert.get("relevant_skill", ""),
                why_recommended=cert.get("why_recommended", ""),
                difficulty=_parse_difficulty(cert.get("difficulty", "intermediate")),
                estimated_time=cert.get("estimated_time", ""),
                url=cert.get("url"),
                cost=cert.get("cost"),
            ))
        except Exception as exc:
            logger.warning("Failed to parse certification: %s", exc)

    # Parse interview prep
    interview_data = result.get("interview_prep", {})
    interview_questions = []
    for q in interview_data.get("questions", []):
        try:
            interview_questions.append(InterviewQuestion(
                question=q.get("question", ""),
                topic=q.get("topic", ""),
                difficulty=_parse_difficulty(q.get("difficulty", "intermediate")),
                tip=q.get("tip", ""),
            ))
        except Exception as exc:
            logger.warning("Failed to parse interview question: %s", exc)

    interview_prep = InterviewPreparation(
        target_role=target_role,
        focus_areas=interview_data.get("focus_areas", []),
        questions=interview_questions,
        general_tips=interview_data.get("general_tips", []),
        why_these_areas=interview_data.get("why_these_areas", ""),
    )

    # Parse career advice
    career_advice = []
    for adv in result.get("career_advice", []):
        try:
            career_advice.append(CareerAdvice(
                title=adv.get("title", ""),
                advice=adv.get("advice", ""),
                relevant_to=adv.get("relevant_to", ""),
                priority=adv.get("priority", "medium"),
                action_items=adv.get("action_items", []),
            ))
        except Exception as exc:
            logger.warning("Failed to parse career advice: %s", exc)

    return FinalCareerPlan(
        student_profile=profile,
        skill_gap=skill_gap,
        roadmap=roadmap,
        courses=courses,
        projects=projects,
        certifications=certs,
        interview_prep=interview_prep,
        career_advice=career_advice,
        target_role=target_role,
        generated_at=datetime.now(timezone.utc).isoformat(),
        input_mode=input_mode,
    )


def _parse_difficulty(value: str) -> Difficulty:
    """Parse difficulty string to enum."""
    value = value.lower().strip()
    if value in ("beginner", "easy"):
        return Difficulty.BEGINNER
    elif value in ("intermediate", "medium"):
        return Difficulty.INTERMEDIATE
    elif value in ("advanced", "hard", "expert"):
        return Difficulty.ADVANCED
    return Difficulty.BEGINNER


def _fallback_plan(
    profile: StudentProfile,
    skill_gap: SkillGapAnalysis,
    target_role: str,
    input_mode: str,
) -> FinalCareerPlan:
    """Generate a basic plan when Gemini is unavailable.

    Produces a simpler but still personalized plan based on the
    skill gap analysis alone.
    """
    # Build roadmap from critical gaps
    steps = []
    for i, gap in enumerate(skill_gap.critical_gaps[:6], 1):
        steps.append(RoadmapStep(
            order=i,
            topic=f"Learn {gap}",
            reason=f"This is a critical requirement for {target_role} that you're currently missing.",
            skills=[gap],
            estimated_duration="2-4 weeks",
            difficulty=Difficulty.INTERMEDIATE,
            prerequisites=[],
            recommended_project=f"Build a project using {gap}",
            recommended_resource=f"Search for '{gap} tutorial' on freeCodeCamp or YouTube",
        ))

    roadmap = LearningRoadmap(
        target_role=target_role,
        steps=steps,
        total_estimated_duration=f"{len(steps) * 3}-{len(steps) * 4} weeks",
        approach_summary=f"Focus on critical gaps first, then build projects to solidify learning.",
    )

    return FinalCareerPlan(
        student_profile=profile,
        skill_gap=skill_gap,
        roadmap=roadmap,
        courses=[],
        projects=[],
        certifications=[],
        interview_prep=InterviewPreparation(target_role=target_role),
        career_advice=[
            CareerAdvice(
                title="Focus on Critical Gaps",
                advice=f"Your readiness score is {skill_gap.career_readiness_score}%. "
                       f"Prioritize learning: {', '.join(skill_gap.critical_gaps[:3])}.",
                relevant_to="Skill Development",
                priority="high",
                action_items=[f"Start learning {gap}" for gap in skill_gap.critical_gaps[:3]],
            ),
        ],
        target_role=target_role,
        generated_at=datetime.now(timezone.utc).isoformat(),
        input_mode=input_mode,
    )
