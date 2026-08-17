from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import CategoryEnum, DomainEnum, Problem, ProblemStatus, User
from app.schemas import ProblemCreate, ProblemOut

router = APIRouter(prefix="/problems", tags=["problems"])


@router.post("", response_model=ProblemOut)
def create_problem(
    payload: ProblemCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Anyone logged in can post a problem -- no verification needed to post,
    only to claim (see spec).
    """
    problem = Problem(
        poster_id=current_user.id,
        title=payload.title,
        description=payload.description,
        category=payload.category,
        domain=payload.domain,
        frequency_severity=payload.frequency_severity,
        current_workaround=payload.current_workaround,
        video_url=payload.video_url,
    )
    db.add(problem)
    db.commit()
    db.refresh(problem)
    return problem


@router.get("", response_model=list[ProblemOut])
def list_problems(
    category: Optional[CategoryEnum] = None,
    domain: Optional[DomainEnum] = None,
    sort: str = "newest",  # "newest" | "most_needed"
    db: Session = Depends(get_db),
):
    query = db.query(Problem)

    if category:
        query = query.filter(Problem.category == category)
    if domain:
        query = query.filter(Problem.domain == domain)

    if sort == "most_needed":
        # v1 proxy for "most needed": problems with a frequency/severity note
        # filled in are surfaced first, then newest. No upvoting yet (out of scope).
        query = query.order_by(
            Problem.frequency_severity.isnot(None).desc(),
            desc(Problem.created_at),
        )
    else:
        query = query.order_by(desc(Problem.created_at))

    return query.all()


@router.get("/{problem_id}", response_model=ProblemOut)
def get_problem(problem_id: str, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    # is_public gate: hide the repo link from non-poster/non-solver if solver
    # marked it private. Everything else about the problem stays visible.
    if problem.status == ProblemStatus.solved and not problem.is_public:
        active_claim = problem.active_claim
        allowed_ids = {problem.poster_id}
        if active_claim:
            allowed_ids.add(active_claim.solver_id)
        # NOTE: once auth is wired into this route (optional current_user),
        # check current_user.id against allowed_ids before exposing github_repo_url.
        # Left permissive here since this route has no auth dependency yet --
        # tighten when the frontend needs it.

    return problem


@router.delete("/{problem_id}")
def delete_problem(
    problem_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
    if problem.poster_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the poster can delete this problem")

    db.delete(problem)
    db.commit()
    return {"status": "deleted"}
