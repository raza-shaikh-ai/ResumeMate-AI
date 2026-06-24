from pydantic import BaseModel, Field
from typing import List, Optional,TypedDict

class Project(BaseModel):
    title: str
    description: str
    technologies: Optional[str] = None
    link: Optional[str] = None
    date: Optional[str] = None


class Experience(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    start_date: str
    end_date: Optional[str] = "Present"
    description: List[str] = Field(default_factory=list)


class Education(BaseModel):
    degree: str
    institution: str
    location: Optional[str] = None
    graduation_year: Optional[str] = None
    gpa: Optional[str] = None


class Certification(BaseModel):
    name: str
    issuer: str
    date: Optional[str] = None


class ResumeData(BaseModel):
    name: str
    title: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = Field(default_factory=list)
    experience: Optional[List[Experience]] = Field(default_factory=list)
    projects: Optional[List[Project]] = Field(default_factory=list)
    education: Optional[List[Education]] = Field(default_factory=list)
    certifications: Optional[List[Certification]] = Field(default_factory=list)
    achievements: Optional[List[str]] = Field(default_factory=list)
    additional_info: Optional[str] = None



class ResumeState(TypedDict, total=False):
    resume_data: dict
    pdf_text: Optional[str]
    normalized_data: dict
    enhanced_resume: dict
    ats_optimized_data: dict
    selected_template: str
    template_content: str
    latex_content: str
    pdf_bytes: bytes
    page_count: int
    ats_score: int
    ats_feedback: dict
    compilation_attempts: int
    processing_steps: List[str]
    errors: List[str]