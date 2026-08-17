"""
Auto-reopens problems whose active claim has had no update in 30+ days.

Run this daily -- e.g. via Render's cron job feature (free tier supports this)
or Windows Task Scheduler for local testing:

    python scripts/reopen_stale_claims.py

Kept as a standalone script rather than an in-process scheduler (APScheduler etc)
so it's stateless and safe to run from any external cron trigger.
"""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models import Claim, ClaimStatus, Problem, ProblemStatus  # noqa: E402

STALE_AFTER_DAYS = 30


def reopen_stale_claims():
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(days=STALE_AFTER_DAYS)

        stale_claims = (
            db.query(Claim)
            .filter(Claim.status == ClaimStatus.in_progress)
            .filter(Claim.last_update_at < cutoff)
            .all()
        )

        if not stale_claims:
            print("No stale claims found.")
            return

        for claim in stale_claims:
            claim.status = ClaimStatus.auto_reopened
            claim.ended_at = datetime.utcnow()

            problem = db.query(Problem).filter(Problem.id == claim.problem_id).first()
            if problem:
                problem.status = ProblemStatus.open

            print(f"Reopened problem {claim.problem_id} (stale claim {claim.id})")

        db.commit()
        print(f"Done -- reopened {len(stale_claims)} problem(s).")
    finally:
        db.close()


if __name__ == "__main__":
    reopen_stale_claims()
