import csv
import uuid
from pathlib import Path

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models import Claim, User


def get_claim(db: Session, claim_id: uuid.UUID) -> Claim | None:
    return db.get(Claim, claim_id)


def create_claim(
    db: Session,
    *,
    claim_id: uuid.UUID | None = None,
    claim_path: str | None,
    invoice_path: str | None,
    policy_path: str | None,
    past_claims_csv_path: str | None = None,
    evidence_file_paths: list[str] | None = None,
    other_file_paths: list[str] | None = None,
) -> Claim:
    c = Claim(
        id=claim_id or uuid.uuid4(),
        status="uploaded",
        claim_file_path=claim_path,
        invoice_file_path=invoice_path,
        policy_file_path=policy_path,
        past_claims_csv_path=past_claims_csv_path,
        evidence_file_paths=evidence_file_paths,
        other_file_paths=other_file_paths,
        processing_logs=[],
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def append_log(db: Session, claim: Claim, message: str) -> None:
    logs = list(claim.processing_logs or [])
    logs.append(message)
    claim.processing_logs = logs
    db.add(claim)
    db.commit()


def save_upload(dest: Path, data: bytes) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return str(dest.resolve())


def summarize_past_claims_csv(path: Path, max_rows: int = 5000) -> dict:
    """Lightweight CSV stats for UX / audit (no full history engine)."""
    try:
        with path.open(newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            rows = list(reader)
        n = max(0, len(rows) - 1) if rows else 0  # assume header
        return {
            "row_count": min(n, max_rows),
            "filename": path.name,
            "columns": rows[0][:24] if rows else [],
        }
    except OSError:
        return {"row_count": 0, "filename": path.name, "columns": [], "error": "unreadable"}


def list_claims(db: Session, *, limit: int = 100, search: str | None = None) -> list[Claim]:
    q = db.query(Claim).order_by(desc(Claim.created_at))
    if search:
        s = search.strip()
        if s:
            try:
                uid = uuid.UUID(s)
                q = q.filter(Claim.id == uid)
            except ValueError:
                q = q.filter(False)  # type: ignore[arg-type]
    return q.limit(limit).all()


def create_user(db: Session, *, username: str, hashed_password: str, email: str, display_name: str | None = None, is_demo: bool = False) -> User:
    u = User(username=username, hashed_password=hashed_password, email=email, display_name=display_name or username, is_demo=is_demo)
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.query(User).filter(User.username == username).first()


def update_user(db: Session, user: User, *, display_name: str | None = None) -> User:
    if display_name is not None:
        user.display_name = display_name
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user_avatar(db: Session, user: User, avatar_path: str) -> User:
    user.avatar_path = avatar_path
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_adjuster_action(db: Session, claim: Claim, action: str) -> Claim:
    from datetime import datetime, timezone

    claim.adjuster_action = action
    claim.adjuster_action_at = datetime.now(timezone.utc)
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim
