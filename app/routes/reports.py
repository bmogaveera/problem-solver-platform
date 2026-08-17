from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Comment, Problem, Report, ReportStatus, ReportTargetType, User
from app.routes.verification import require_admin
from app.schemas import ReportCreate

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("")
def create_report(
    payload: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.target_type == "problem":
        target_type = ReportTargetType.problem
        exists = db.query(Problem).filter(Problem.id == payload.target_id).first()
    elif payload.target_type == "comment":
        target_type = ReportTargetType.comment
        exists = db.query(Comment).filter(Comment.id == payload.target_id).first()
    else:
        raise HTTPException(status_code=400, detail="target_type must be 'problem' or 'comment'")

    if not exists:
        raise HTTPException(status_code=404, detail=f"{payload.target_type} not found")

    report = Report(
        target_type=target_type,
        target_id=payload.target_id,
        reporter_id=current_user.id,
        reason=payload.reason,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return {
        "id": report.id,
        "target_type": report.target_type.value,
        "target_id": report.target_id,
        "reason": report.reason,
        "status": report.status.value,
        "created_at": report.created_at,
    }


@router.get("/queue")
def list_pending_reports(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only queue -- no auto-removal, just surfaced here for manual review."""
    reports = db.query(Report).filter(Report.status == ReportStatus.pending).all()
    return [
        {
            "id": r.id,
            "target_type": r.target_type.value,
            "target_id": r.target_id,
            "reporter_id": r.reporter_id,
            "reason": r.reason,
            "status": r.status.value,
            "created_at": r.created_at,
        }
        for r in reports
    ]


@router.patch("/{report_id}/resolve")
def resolve_report(
    report_id: str,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = ReportStatus.reviewed
    db.commit()
    return {"status": "reviewed", "report_id": report.id}
