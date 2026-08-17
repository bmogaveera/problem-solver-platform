from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Claim, ClaimStatus, Problem, ProblemStatus, User
from app.schemas import ClaimOut

router = APIRouter(prefix="/problems", tags=["claims"])


@router.post("/{problem_id}/claim", response_model=ClaimOut)
def claim_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_verified_solver:
        raise HTTPException(
            status_code=403,
            detail="Only approved, non-expired verified solvers can claim problems",
        )

    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    if problem.status != ProblemStatus.open:
        raise HTTPException(
            status_code=400,
            detail=f"Problem is not open (current status: {problem.status.value})",
        )

    if problem.poster_id == current_user.id:
        raise HTTPException(status_code=400, detail="You can't claim your own problem")

    claim = Claim(problem_id=problem.id, solver_id=current_user.id)
    db.add(claim)
    problem.status = ProblemStatus.claimed
    db.commit()
    db.refresh(claim)
    return claim


@router.post("/{problem_id}/unclaim")
def unclaim_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    active_claim = problem.active_claim
    if not active_claim:
        raise HTTPException(status_code=400, detail="This problem has no active claim")
    if active_claim.solver_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't hold the active claim on this problem")

    active_claim.status = ClaimStatus.unclaimed
    active_claim.ended_at = datetime.utcnow()
    problem.status = ProblemStatus.open
    db.commit()
    return {"status": "unclaimed", "problem_status": "open"}


@router.get("/mine/claims", response_model=list[ClaimOut])
def my_claims(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """All claims (active + past) held by the current user."""
    return db.query(Claim).filter(Claim.solver_id == current_user.id).all()
