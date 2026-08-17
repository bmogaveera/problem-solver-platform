from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models import CategoryEnum, ClaimStatus, DomainEnum, ProblemStatus, VerificationStatus


# ---------- User ----------

class UserOut(BaseModel):
    id: str
    username: str
    avatar_url: Optional[str] = None
    is_verified_solver: bool = False

    class Config:
        from_attributes = True


# ---------- ID Verification ----------

class IDVerificationSubmit(BaseModel):
    photo_url: str  # uploaded to Supabase first, URL passed here


class IDVerificationOut(BaseModel):
    id: str
    status: VerificationStatus
    valid_until: Optional[datetime] = None
    submitted_at: datetime

    class Config:
        from_attributes = True


class IDVerificationReview(BaseModel):
    status: VerificationStatus  # approved / rejected
    valid_until: Optional[datetime] = None  # admin can override default +4yr
    reviewer_note: Optional[str] = None


# ---------- Problem ----------

class ProblemCreate(BaseModel):
    title: str
    description: str
    category: CategoryEnum
    domain: DomainEnum
    frequency_severity: Optional[str] = None
    current_workaround: Optional[str] = None
    video_url: Optional[str] = None


class ProblemOut(BaseModel):
    id: str
    title: str
    description: str
    category: CategoryEnum
    domain: DomainEnum
    frequency_severity: Optional[str]
    current_workaround: Optional[str]
    video_url: Optional[str]
    status: ProblemStatus
    github_repo_url: Optional[str]
    is_public: bool
    poster: UserOut
    created_at: datetime

    class Config:
        from_attributes = True


class ProblemFilter(BaseModel):
    category: Optional[CategoryEnum] = None
    domain: Optional[DomainEnum] = None
    sort: Optional[str] = "newest"  # "newest" | "most_needed"


# ---------- Claim ----------

class ClaimOut(BaseModel):
    id: str
    problem_id: str
    solver: UserOut
    status: ClaimStatus
    claimed_at: datetime

    class Config:
        from_attributes = True


class SolutionSubmit(BaseModel):
    github_repo_url: str
    is_public: bool = True


# ---------- Comment ----------

class CommentCreate(BaseModel):
    content: str


class CommentOut(BaseModel):
    id: str
    content: str
    user: UserOut
    is_flagged: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ---------- Report ----------

class ReportCreate(BaseModel):
    target_type: str  # "problem" | "comment"
    target_id: str
    reason: str
