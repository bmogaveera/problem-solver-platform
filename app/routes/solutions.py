from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Problem, ProblemStatus, User
from app.schemas import ProblemOut, SolutionSubmit

router = APIRouter(prefix="/problems", tags=["solutions"])


@router.post("/{problem_id}/solution", response_model=ProblemOut)
def submit_solution(
    problem_id: str,
    payload: SolutionSubmit,
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
        raise HTTPException(
            status_code=403,
            detail="Only the solver holding the active claim can submit a solution",
        )

    problem.github_repo_url = payload.github_repo_url
    problem.is_public = payload.is_public
    problem.status = ProblemStatus.solved
    problem.solved_at = datetime.utcnow()

    # bump last_update_at so this claim doesn't look stale right before closing
    active_claim.last_update_at = datetime.utcnow()

    db.commit()
    db.refresh(problem)
    return problem
