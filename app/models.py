import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, Integer, String, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


# ---------- ENUMS ----------

class CategoryEnum(str, enum.Enum):
    civil = "civil"
    engineering = "engineering"


class DomainEnum(str, enum.Enum):
    software_web = "Software/Web Development"
    mobile = "Mobile App Development"
    iot_hardware = "IoT / Hardware"
    ai_ml = "AI / Machine Learning"
    data_analytics = "Data / Analytics"
    civil_infra = "Civil Infrastructure"
    environment = "Environment / Sustainability"
    healthcare = "Healthcare"
    education = "Education"
    transportation = "Transportation / Mobility"
    other = "Other"


class ProblemStatus(str, enum.Enum):
    open = "open"
    claimed = "claimed"
    solved = "solved"


class VerificationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class ClaimStatus(str, enum.Enum):
    in_progress = "in_progress"
    unclaimed = "unclaimed"
    auto_reopened = "auto_reopened"


class ReportTargetType(str, enum.Enum):
    problem = "problem"
    comment = "comment"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"


# ---------- CORE TABLES ----------

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    github_id = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=False)
    email = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    verification = relationship("IDVerification", back_populates="user", uselist=False)
    problems_posted = relationship("Problem", back_populates="poster", foreign_keys="Problem.poster_id")
    claims = relationship("Claim", back_populates="solver")
    comments = relationship("Comment", back_populates="user")

    @property
    def is_verified_solver(self) -> bool:
        v = self.verification
        if not v or v.status != VerificationStatus.approved:
            return False
        return v.valid_until is None or v.valid_until > datetime.utcnow()


class IDVerification(Base):
    __tablename__ = "id_verifications"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False)
    photo_url = Column(String, nullable=False)  # Supabase Storage URL
    status = Column(Enum(VerificationStatus), default=VerificationStatus.pending, nullable=False)
    valid_until = Column(DateTime, nullable=True)  # default +4 years on approval, adjustable
    reviewer_note = Column(Text, nullable=True)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="verification")


class Problem(Base):
    __tablename__ = "problems"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    poster_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    category = Column(Enum(CategoryEnum), nullable=False)
    domain = Column(Enum(DomainEnum), nullable=False)
    frequency_severity = Column(Text, nullable=True)
    current_workaround = Column(Text, nullable=True)
    video_url = Column(String, nullable=True)  # Supabase Storage, ~50MB cap enforced at upload

    status = Column(Enum(ProblemStatus), default=ProblemStatus.open, nullable=False)

    # solution fields, populated when solved
    github_repo_url = Column(String, nullable=True)
    is_public = Column(Boolean, default=True)
    solved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    poster = relationship("User", back_populates="problems_posted", foreign_keys=[poster_id])
    claims = relationship("Claim", back_populates="problem")
    comments = relationship("Comment", back_populates="problem")

    @property
    def active_claim(self):
        return next((c for c in self.claims if c.status == ClaimStatus.in_progress), None)


class Claim(Base):
    """
    Full history of claim attempts on a problem (kept for audit trail --
    unclaim/reclaim happens, so this isn't just one row per problem).
    Only one row per problem should have status == in_progress at a time;
    enforce that in the route logic, not the DB.
    """
    __tablename__ = "claims"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    problem_id = Column(UUID(as_uuid=False), ForeignKey("problems.id"), nullable=False)
    solver_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    status = Column(Enum(ClaimStatus), default=ClaimStatus.in_progress, nullable=False)
    claimed_at = Column(DateTime, default=datetime.utcnow)
    last_update_at = Column(DateTime, default=datetime.utcnow)  # bump this on any solver activity
    ended_at = Column(DateTime, nullable=True)  # unclaim time or auto-reopen time

    problem = relationship("Problem", back_populates="claims")
    solver = relationship("User", back_populates="claims")


class Comment(Base):
    __tablename__ = "comments"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    problem_id = Column(UUID(as_uuid=False), ForeignKey("problems.id"), nullable=False)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    content = Column(Text, nullable=False)
    is_flagged = Column(Boolean, default=False)  # profanity filter hit
    created_at = Column(DateTime, default=datetime.utcnow)

    problem = relationship("Problem", back_populates="comments")
    user = relationship("User", back_populates="comments")


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    target_type = Column(Enum(ReportTargetType), nullable=False)
    target_id = Column(UUID(as_uuid=False), nullable=False)  # problem.id or comment.id
    reporter_id = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=False)

    reason = Column(String, nullable=False)  # spam / fake / abusive / other
    status = Column(Enum(ReportStatus), default=ReportStatus.pending, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
