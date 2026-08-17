from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import IDVerification, User, VerificationStatus
from app.schemas import IDVerificationOut, IDVerificationReview, IDVerificationSubmit

router = APIRouter(prefix="/verification", tags=["verification"])

DEFAULT_VALID_YEARS = 4


@router.post("", response_model=IDVerificationOut)
def submit_verification(
    payload: IDVerificationSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    photo_url should already point to a file uploaded to Supabase Storage --
    this route just records it and puts the user in the review queue.
    """
    existing = db.query(IDVerification).filter(
        IDVerification.user_id == current_user.id
    ).first()

    if existing:
        # allow resubmission if previously rejected; otherwise block duplicates
        if existing.status == VerificationStatus.rejected:
            existing.photo_url = payload.photo_url
            existing.status = VerificationStatus.pending
            existing.submitted_at = datetime.utcnow()
            existing.reviewed_at = None
            existing.reviewer_note = None
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(
            status_code=400,
            detail=f"Verification already {existing.status.value}",
        )

    verification = IDVerification(
        user_id=current_user.id,
        photo_url=payload.photo_url,
    )
    db.add(verification)
    db.commit()
    db.refresh(verification)
    return verification


@router.get("/me", response_model=IDVerificationOut)
def get_my_verification(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    verification = db.query(IDVerification).filter(
        IDVerification.user_id == current_user.id
    ).first()
    if not verification:
        raise HTTPException(status_code=404, detail="No verification submitted yet")
    return verification


# ---------- Admin-only review ----------
# NOTE: v1 has no real admin role system yet. This is gated by a simple
# hardcoded check against your own GitHub username for now -- swap this
# for a proper `is_admin` flag on User once you have more than one reviewer.

ADMIN_USERNAMES = {"bmogaveera"}  # TODO: move to .env or a proper roles table


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.username not in ADMIN_USERNAMES:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/queue", response_model=list[IDVerificationOut])
def list_pending_verifications(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return db.query(IDVerification).filter(
        IDVerification.status == VerificationStatus.pending
    ).all()


@router.patch("/{verification_id}", response_model=IDVerificationOut)
def review_verification(
    verification_id: str,
    payload: IDVerificationReview,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    verification = db.query(IDVerification).filter(
        IDVerification.id == verification_id
    ).first()
    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    verification.status = payload.status
    verification.reviewer_note = payload.reviewer_note
    verification.reviewed_at = datetime.utcnow()

    if payload.status == VerificationStatus.approved:
        verification.valid_until = payload.valid_until or (
            datetime.utcnow() + timedelta(days=365 * DEFAULT_VALID_YEARS)
        )
    else:
        verification.valid_until = None

    db.commit()
    db.refresh(verification)
    return verification
