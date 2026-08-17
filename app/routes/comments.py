from better_profanity import profanity
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Comment, Problem, User
from app.schemas import CommentCreate, CommentOut

router = APIRouter(prefix="/problems", tags=["comments"])

profanity.load_censor_words()


@router.post("/{problem_id}/comments", response_model=CommentOut)
def create_comment(
    problem_id: str,
    payload: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    is_flagged = profanity.contains_profanity(payload.content)

    comment = Comment(
        problem_id=problem.id,
        user_id=current_user.id,
        content=payload.content,
        is_flagged=is_flagged,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get("/{problem_id}/comments", response_model=list[CommentOut])
def list_comments(problem_id: str, db: Session = Depends(get_db)):
    problem = db.query(Problem).filter(Problem.id == problem_id).first()
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    return (
        db.query(Comment)
        .filter(Comment.problem_id == problem_id)
        .order_by(Comment.created_at.asc())
        .all()
    )
